"""
PixelShield – LSB Steganography
Hide arbitrary bytes inside an RGB carrier image using Least-Significant-Bit
encoding. The hidden data is invisibly embedded in the lowest bit of each
colour channel, causing a maximum pixel-value change of ±1.

Security notes
--------------
* LSB steganography alone is NOT encryption.
* PixelShield optionally AES-256-GCM encrypts the payload before embedding,
  so the carrier image reveals only random noise — not the plaintext.
* The carrier image MUST be saved losslessly (PNG). JPEG compression
  destroys LSB data.

Container (embedded header inside the carrier):
    [4B: payload_len][payload_bytes]
All values are big-endian.

Password-based encryption format (when *password* is supplied):
    embedded payload = [16B: argon2id_salt][AES-256-GCM ciphertext]
The salt is stored unencrypted inside the carrier so that ``extract`` can
rederive the exact same key from the password.  Supplying a raw *key* instead
skips salt embedding (used by unit tests and programmatic callers that manage
key derivation externally).
"""

from __future__ import annotations

import io
import os
import struct
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


_HEADER_BYTES = 4       # stores payload length
_BITS_PER_BYTE = 8
_CHANNELS = 3           # R, G, B
_SALT_BYTES = 16        # KDF salt prepended to ciphertext when password is used


def _capacity_bytes(arr: np.ndarray) -> int:
    """Maximum payload capacity of *arr* in bytes (excluding 4-byte header)."""
    total_bits = arr.shape[0] * arr.shape[1] * _CHANNELS
    total_bytes = total_bits // _BITS_PER_BYTE
    return total_bytes - _HEADER_BYTES


class LSBSteganography:
    """Embed and extract arbitrary bytes in/from an RGB image via LSB encoding.

    Two encryption modes are supported:

    * **Password mode** (recommended for CLI use): pass ``password``.
      A random 16-byte Argon2id salt is generated at embed-time, prepended to
      the AES-256-GCM ciphertext, and stored inside the carrier image.
      ``extract`` reads the salt back, rederives the key, and decrypts.

    * **Key mode** (for programmatic / test use): pass a 32-byte ``key``.
      No salt is embedded; the caller is responsible for key management.

    Args:
        encrypt_payload: Whether to AES-256-GCM encrypt the payload.
        key:             32-byte AES key (key mode; mutually exclusive with *password*).
        password:        Plaintext password (password mode; mutually exclusive with *key*).
    """

    def __init__(
        self,
        encrypt_payload: bool = True,
        key: Optional[bytes] = None,
        password: Optional[str] = None,
    ) -> None:
        if encrypt_payload and key is not None and password is not None:
            raise ValueError("Supply either 'key' or 'password', not both.")
        if encrypt_payload and key is None and password is None:
            raise ValueError(
                "encrypt_payload=True requires either a 32-byte 'key' or a 'password'."
            )
        if encrypt_payload and key is not None and len(key) != 32:
            raise ValueError("A 32-byte AES key is required when encrypt_payload=True.")

        self._encrypt = encrypt_payload
        self._key = key                     # None when password mode
        self._password = password           # None when key mode
        self._password_mode = encrypt_payload and password is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(
        self,
        carrier_path: str | Path,
        payload: bytes,
        output_path: str | Path,
    ) -> int:
        """Embed *payload* into *carrier_path* and save the result to *output_path*.

        In password mode a fresh 16-byte Argon2id salt is generated, the
        payload is AES-256-GCM encrypted, and ``[salt | ciphertext]`` is what
        gets embedded.  ``extract`` will recover the salt and rederive the key
        automatically.

        Args:
            carrier_path: Path to the host PNG/BMP image (lossless).
            payload:      Raw bytes to hide.
            output_path:  Destination path for the stego image (PNG).

        Returns:
            Number of original (pre-encryption) payload bytes embedded.

        Raises:
            ValueError: If the carrier is too small to hold the payload.
        """
        carrier = Image.open(carrier_path).convert("RGB")
        arr = np.array(carrier, dtype=np.uint8)

        if self._encrypt:
            if self._password_mode:
                salt = os.urandom(_SALT_BYTES)
                key = self._derive_key(self._password, salt)
                ciphertext = self._aes_encrypt_with_key(payload, key)
                payload_to_embed = salt + ciphertext
            else:
                payload_to_embed = self._aes_encrypt_with_key(payload, self._key)
        else:
            payload_to_embed = payload

        original_len = len(payload)
        capacity = _capacity_bytes(arr)
        if len(payload_to_embed) > capacity:
            raise ValueError(
                f"Payload too large: {len(payload_to_embed)} bytes; "
                f"carrier capacity is {capacity} bytes."
            )

        # Prepend 4-byte big-endian length.
        header = struct.pack(">I", len(payload_to_embed))
        data = header + payload_to_embed

        arr_flat = arr.flatten().astype(np.uint8)
        data_bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        # Clear LSB of each channel byte, then set it from the payload bit.
        arr_flat[: len(data_bits)] = (arr_flat[: len(data_bits)] & 0xFE) | data_bits
        stego_arr = arr_flat.reshape(arr.shape)

        out_img = Image.fromarray(stego_arr, mode="RGB")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out_img.save(str(output_path), format="PNG")
        return original_len

    def extract(self, stego_path: str | Path) -> bytes:
        """Extract a hidden payload from *stego_path*.

        In password mode the first ``_SALT_BYTES`` bytes of the embedded data
        are treated as the KDF salt; the key is rederived and used to decrypt
        the rest.

        Args:
            stego_path: Path to the stego image (PNG).

        Returns:
            Decrypted (or raw) payload bytes.

        Raises:
            ValueError: If no payload header is detected or decryption fails.
        """
        arr = np.array(Image.open(stego_path).convert("RGB"), dtype=np.uint8)
        arr_flat = arr.flatten()

        # Read header (4 bytes × 8 bits = 32 bits).
        header_bits = (arr_flat[:32] & 1).astype(np.uint8)
        header_bytes_arr = np.packbits(header_bits)
        payload_len = struct.unpack(">I", bytes(header_bytes_arr))[0]

        capacity = _capacity_bytes(arr)
        if payload_len > capacity:
            raise ValueError(
                f"Invalid payload length {payload_len}: "
                "carrier image may not contain a PixelShield payload."
            )
        if payload_len == 0:
            return b""

        # Extract embedded bytes.
        total_bits = (payload_len + _HEADER_BYTES) * _BITS_PER_BYTE
        raw_bits = (arr_flat[:total_bits] & 1).astype(np.uint8)
        raw_bytes = bytes(np.packbits(raw_bits))
        embedded = raw_bytes[_HEADER_BYTES:]

        if self._encrypt:
            if self._password_mode:
                if len(embedded) < _SALT_BYTES:
                    raise ValueError("Embedded data too short to contain a KDF salt.")
                salt = embedded[:_SALT_BYTES]
                ciphertext = embedded[_SALT_BYTES:]
                key = self._derive_key(self._password, salt)
                return self._aes_decrypt_with_key(ciphertext, key)
            else:
                return self._aes_decrypt_with_key(embedded, self._key)

        return embedded

    def capacity(self, carrier_path: str | Path) -> dict:
        """Return the available steganographic capacity of *carrier_path*.

        Args:
            carrier_path: Path to the carrier image.

        Returns:
            Dict with ``width``, ``height``, ``capacity_bytes``, and ``capacity_kb``.
        """
        arr = np.array(Image.open(carrier_path).convert("RGB"))
        cap = _capacity_bytes(arr)
        return {
            "width": arr.shape[1],
            "height": arr.shape[0],
            "capacity_bytes": cap,
            "capacity_kb": round(cap / 1024, 2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """Derive a 32-byte AES key from *password* and *salt* via Argon2id."""
        from security.password import PasswordManager
        pm = PasswordManager(hash_len=32)
        return pm.derive_key(password, salt)

    @staticmethod
    def _aes_encrypt_with_key(plaintext: bytes, key: bytes) -> bytes:
        from core.aes import AESCipher
        return AESCipher(key).encrypt(plaintext, mode="gcm")

    @staticmethod
    def _aes_decrypt_with_key(ciphertext: bytes, key: bytes) -> bytes:
        from core.aes import AESCipher
        return AESCipher(key).decrypt(ciphertext, mode="gcm")
