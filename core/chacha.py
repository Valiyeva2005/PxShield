"""
PixelShield – ChaCha20-Poly1305 Cipher
Stream cipher alternative to AES-GCM. Preferred in environments without
hardware AES acceleration (mobile, embedded, low-end ARM).

ChaCha20-Poly1305 is standardised in RFC 8439 and is the cipher used in
TLS 1.3 (IETF ChaCha20) and WireGuard.

Container format::

    [nonce (12B)] [tag (16B)] [ciphertext]
"""

from __future__ import annotations

import os

from Crypto.Cipher import ChaCha20_Poly1305

_NONCE_LEN = 12     # 96-bit nonce (RFC 8439)
_TAG_LEN   = 16     # 128-bit Poly1305 authentication tag
_KEY_LEN   = 32     # 256-bit key


class ChaCha20Cipher:
    """ChaCha20-Poly1305 authenticated stream cipher.

    Args:
        key: 32-byte secret key (AES-256 strength).

    Raises:
        ValueError: If *key* is not exactly 32 bytes.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != _KEY_LEN:
            raise ValueError(f"Key must be exactly {_KEY_LEN} bytes, got {len(key)}.")
        self._key = key

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        """Encrypt *plaintext* with ChaCha20-Poly1305.

        Args:
            plaintext: Raw bytes to encrypt.
            aad:       Additional Authenticated Data (not encrypted).

        Returns:
            Packed bytes: ``[nonce (12B)][tag (16B)][ciphertext]``.
        """
        nonce = os.urandom(_NONCE_LEN)
        cipher = ChaCha20_Poly1305.new(key=self._key, nonce=nonce)
        if aad:
            cipher.update(aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return nonce + tag + ciphertext

    def decrypt(self, data: bytes, aad: bytes = b"") -> bytes:
        """Decrypt ChaCha20-Poly1305 *data*.

        Args:
            data: Packed bytes (nonce + tag + ciphertext).
            aad:  AAD used during encryption.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            ValueError: On authentication failure or malformed input.
        """
        min_len = _NONCE_LEN + _TAG_LEN
        if len(data) < min_len:
            raise ValueError(
                f"ChaCha20 data too short: expected ≥{min_len} bytes, got {len(data)}."
            )
        nonce      = data[:_NONCE_LEN]
        tag        = data[_NONCE_LEN: _NONCE_LEN + _TAG_LEN]
        ciphertext = data[_NONCE_LEN + _TAG_LEN:]

        cipher = ChaCha20_Poly1305.new(key=self._key, nonce=nonce)
        if aad:
            cipher.update(aad)
        try:
            return cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError as exc:
            raise ValueError(
                "ChaCha20-Poly1305 authentication failed – data may be tampered."
            ) from exc
