"""
PixelShield – Password & Key Derivation
Argon2id-based key derivation; never stores raw passwords.
"""

from __future__ import annotations

import os
import secrets

from argon2 import PasswordHasher
from argon2.low_level import Type, hash_secret_raw

from utils.config import config


class PasswordManager:
    """Derives cryptographic keys from user passwords using Argon2id.

    Argon2id is the OWASP-recommended algorithm for password hashing and
    key derivation.  Keys are derived fresh on each call and are never
    persisted.

    Args:
        time_cost:    Number of iterations (default from config).
        memory_cost:  Memory usage in KiB (default from config).
        parallelism:  Degree of parallelism (default from config).
        hash_len:     Output key length in bytes (default from config).
    """

    def __init__(
        self,
        time_cost: int | None = None,
        memory_cost: int | None = None,
        parallelism: int | None = None,
        hash_len: int | None = None,
    ) -> None:
        self.time_cost = time_cost or config.get("security.argon2_time_cost", 3)
        self.memory_cost = memory_cost or config.get("security.argon2_memory_cost", 65536)
        self.parallelism = parallelism or config.get("security.argon2_parallelism", 4)
        self.hash_len = hash_len or config.get("security.argon2_hash_len", 32)

    def generate_salt(self) -> bytes:
        """Generate a cryptographically secure random salt (16 bytes)."""
        return secrets.token_bytes(16)

    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive a fixed-length key from *password* and *salt*.

        Args:
            password: User-supplied plaintext password.
            salt:     Random salt (must be stored alongside the ciphertext).

        Returns:
            Raw key bytes of length ``self.hash_len``.
        """
        if not password:
            raise ValueError("Password must not be empty.")
        if len(salt) < 8:
            raise ValueError("Salt must be at least 8 bytes.")

        key: bytes = hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=self.hash_len,
            type=Type.ID,
        )
        return key

    def derive_seed(self, password: str, salt: bytes) -> int:
        """Derive a deterministic integer seed for NumPy RNG operations.

        Args:
            password: User-supplied plaintext password.
            salt:     Salt used during key derivation.

        Returns:
            Non-negative integer seed (fits in a 64-bit unsigned int).
        """
        raw = self.derive_key(password, salt)
        # Use the first 8 bytes as a big-endian uint64.
        return int.from_bytes(raw[:8], "big")


# Module-level singleton with default configuration.
password_manager = PasswordManager()
