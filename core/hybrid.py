"""
PixelShield – Hybrid Encryption
Combines RSA-2048 public-key encryption for key wrapping with AES-256-GCM
for data encryption. This is the "envelope encryption" pattern used in
professional cryptographic systems (GPG, AWS KMS, etc.).

Flow:
  Encrypt:
    1. Generate a random 32-byte session key.
    2. Encrypt image bytes with AES-256-GCM using the session key.
    3. Encrypt the session key with RSA-OAEP-SHA256.
    4. Bundle: [2B RSA len][RSA-encrypted session key][nonce][tag][ciphertext].

  Decrypt:
    1. Unwrap the session key with the RSA private key.
    2. Decrypt the AES ciphertext with the unwrapped session key.
"""

from __future__ import annotations

import os
from pathlib import Path

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Hash import SHA256

_KEY_BITS = 2048
_SESSION_KEY_LEN = 32   # bytes (AES-256)
_NONCE_LEN = 16
_TAG_LEN = 16


class HybridKeyPair:
    """RSA-2048 key-pair container.

    Args:
        private_key: RSA private key object.
        public_key:  RSA public key object.
    """

    def __init__(self, private_key: RSA.RsaKey, public_key: RSA.RsaKey) -> None:
        self.private_key = private_key
        self.public_key = public_key

    @classmethod
    def generate(cls) -> "HybridKeyPair":
        """Generate a fresh RSA-2048 key pair."""
        private_key = RSA.generate(_KEY_BITS)
        return cls(private_key=private_key, public_key=private_key.publickey())

    @classmethod
    def load(cls, private_key_path: str | Path) -> "HybridKeyPair":
        """Load an RSA key pair from a PEM private key file.

        Args:
            private_key_path: Path to the PEM-encoded RSA private key.

        Returns:
            :class:`HybridKeyPair` instance.
        """
        pem = Path(private_key_path).read_bytes()
        private_key = RSA.import_key(pem)
        return cls(private_key=private_key, public_key=private_key.publickey())

    def save(self, private_key_path: str | Path, public_key_path: str | Path) -> None:
        """Export both keys as PEM files.

        Args:
            private_key_path: Destination for the private key PEM.
            public_key_path:  Destination for the public key PEM.
        """
        Path(private_key_path).parent.mkdir(parents=True, exist_ok=True)
        Path(public_key_path).parent.mkdir(parents=True, exist_ok=True)
        Path(private_key_path).write_bytes(self.private_key.export_key("PEM"))
        Path(public_key_path).write_bytes(self.public_key.export_key("PEM"))

    def public_key_pem(self) -> bytes:
        """Return the public key as PEM bytes."""
        return self.public_key.export_key("PEM")

    def private_key_pem(self) -> bytes:
        """Return the private key as PEM bytes."""
        return self.private_key.export_key("PEM")


class HybridCipher:
    """Hybrid RSA + AES-256-GCM encryption.

    Args:
        key_pair: RSA key pair for session key wrapping.
    """

    def __init__(self, key_pair: HybridKeyPair) -> None:
        self._kp = key_pair

    def _rsa_encrypt(self, data: bytes) -> bytes:
        cipher = PKCS1_OAEP.new(self._kp.public_key, hashAlgo=SHA256)
        return cipher.encrypt(data)

    def _rsa_decrypt(self, data: bytes) -> bytes:
        cipher = PKCS1_OAEP.new(self._kp.private_key, hashAlgo=SHA256)
        return cipher.decrypt(data)

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        """Encrypt *plaintext* with a fresh AES-256-GCM session key wrapped by RSA.

        Output format::

            [2B: RSA ciphertext len][RSA-encrypted session key]
            [nonce (16B)][tag (16B)][AES ciphertext]

        Args:
            plaintext: Raw bytes to encrypt.
            aad:       Optional Additional Authenticated Data.

        Returns:
            Packed hybrid ciphertext bytes.
        """
        session_key = os.urandom(_SESSION_KEY_LEN)
        nonce = os.urandom(_NONCE_LEN)

        # AES-256-GCM encryption of the plaintext.
        aes_cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce, mac_len=_TAG_LEN)
        if aad:
            aes_cipher.update(aad)
        ciphertext, tag = aes_cipher.encrypt_and_digest(plaintext)

        # RSA-OAEP wrap the session key.
        wrapped_key = self._rsa_encrypt(session_key)
        key_len = len(wrapped_key).to_bytes(2, "big")

        return key_len + wrapped_key + nonce + tag + ciphertext

    def decrypt(self, data: bytes, aad: bytes = b"") -> bytes:
        """Decrypt hybrid *data*.

        Args:
            data: Packed hybrid ciphertext.
            aad:  AAD used during encryption.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            ValueError: On authentication failure or malformed input.
        """
        if len(data) < 2:
            raise ValueError("Hybrid ciphertext is too short.")

        key_len = int.from_bytes(data[:2], "big")
        offset = 2
        wrapped_key = data[offset: offset + key_len]
        offset += key_len

        nonce = data[offset: offset + _NONCE_LEN]
        offset += _NONCE_LEN
        tag = data[offset: offset + _TAG_LEN]
        offset += _TAG_LEN
        ciphertext = data[offset:]

        # Unwrap session key with RSA private key.
        session_key = self._rsa_decrypt(wrapped_key)

        # AES-256-GCM decryption.
        aes_cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce, mac_len=_TAG_LEN)
        if aad:
            aes_cipher.update(aad)
        try:
            plaintext = aes_cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError as exc:
            raise ValueError(
                "Hybrid decryption authentication failed – ciphertext may be tampered."
            ) from exc
        return plaintext
