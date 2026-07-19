"""
PixelShield – AES-256 Encryption / Decryption
Supports CBC (with PKCS7 padding) and GCM (authenticated) modes.
"""

from __future__ import annotations

import os
import struct

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

IV_SIZE = 16        # bytes
TAG_SIZE = 16       # bytes (GCM authentication tag)
NONCE_SIZE = 16     # bytes (GCM nonce)


class AESCipher:
    """AES-256 cipher wrapper supporting CBC and GCM modes.

    Args:
        key: 32-byte encryption key.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError(f"AES-256 requires a 32-byte key; got {len(key)} bytes.")
        self._key = key

    # ------------------------------------------------------------------
    # GCM (authenticated encryption with associated data)
    # ------------------------------------------------------------------

    def encrypt_gcm(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        """Encrypt *plaintext* using AES-256-GCM.

        Output format::

            [nonce (16 B)] [tag (16 B)] [ciphertext]

        Args:
            plaintext: Raw bytes to encrypt.
            aad:       Additional authenticated data (not encrypted).

        Returns:
            Packed bytes: nonce + authentication tag + ciphertext.
        """
        nonce = os.urandom(NONCE_SIZE)
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce, mac_len=TAG_SIZE)
        if aad:
            cipher.update(aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return nonce + tag + ciphertext

    def decrypt_gcm(self, data: bytes, aad: bytes = b"") -> bytes:
        """Decrypt AES-256-GCM *data*.

        Args:
            data: Packed bytes: nonce + tag + ciphertext.
            aad:  Additional authenticated data used during encryption.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            ValueError: On authentication failure (tag mismatch).
        """
        if len(data) < NONCE_SIZE + TAG_SIZE:
            raise ValueError("Encrypted data is too short for GCM header.")
        nonce = data[:NONCE_SIZE]
        tag = data[NONCE_SIZE: NONCE_SIZE + TAG_SIZE]
        ciphertext = data[NONCE_SIZE + TAG_SIZE:]
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce, mac_len=TAG_SIZE)
        if aad:
            cipher.update(aad)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError as exc:
            raise ValueError(
                "GCM authentication failed – ciphertext may have been tampered with."
            ) from exc
        return plaintext

    # ------------------------------------------------------------------
    # CBC (with PKCS7 padding)
    # ------------------------------------------------------------------

    def encrypt_cbc(self, plaintext: bytes) -> bytes:
        """Encrypt *plaintext* using AES-256-CBC with PKCS7 padding.

        Output format::

            [IV (16 B)] [ciphertext]

        Args:
            plaintext: Raw bytes to encrypt.

        Returns:
            Packed bytes: IV + ciphertext.
        """
        iv = os.urandom(IV_SIZE)
        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        return iv + ciphertext

    def decrypt_cbc(self, data: bytes) -> bytes:
        """Decrypt AES-256-CBC *data*.

        Args:
            data: Packed bytes: IV + ciphertext.

        Returns:
            Decrypted plaintext bytes.
        """
        if len(data) < IV_SIZE:
            raise ValueError("Encrypted data is too short for CBC IV.")
        iv = data[:IV_SIZE]
        ciphertext = data[IV_SIZE:]
        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(ciphertext), AES.block_size)

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: bytes, mode: str = "gcm", aad: bytes = b"") -> bytes:
        """Encrypt *plaintext* using the specified *mode*.

        Args:
            plaintext: Bytes to encrypt.
            mode:      ``"gcm"`` (default) or ``"cbc"``.
            aad:       Optional AAD for GCM mode.

        Returns:
            Encrypted bytes (mode-specific format).
        """
        if mode == "gcm":
            return self.encrypt_gcm(plaintext, aad=aad)
        if mode == "cbc":
            return self.encrypt_cbc(plaintext)
        raise ValueError(f"Unknown AES mode: {mode!r}")

    def decrypt(self, data: bytes, mode: str = "gcm", aad: bytes = b"") -> bytes:
        """Decrypt *data* using the specified *mode*.

        Args:
            data: Encrypted bytes.
            mode: ``"gcm"`` (default) or ``"cbc"``.
            aad:  Optional AAD for GCM mode.

        Returns:
            Decrypted plaintext bytes.
        """
        if mode == "gcm":
            return self.decrypt_gcm(data, aad=aad)
        if mode == "cbc":
            return self.decrypt_cbc(data)
        raise ValueError(f"Unknown AES mode: {mode!r}")
