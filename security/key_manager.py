"""
PixelShield – Key Manager
Handles key generation, storage metadata, and retrieval.
Keys are never persisted in plaintext; only salts and algorithm params are stored.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from security.password import PasswordManager


@dataclass
class KeyMaterial:
    """Encapsulates all data needed to reproduce a key.

    Attributes:
        salt:         Hex-encoded random salt used in derivation.
        algorithm:    Encryption algorithm identifier.
        key_size:     Key length in bytes.
        time_cost:    Argon2id time cost parameter.
        memory_cost:  Argon2id memory cost parameter (KiB).
        parallelism:  Argon2id parallelism parameter.
    """

    salt: str  # hex-encoded bytes
    algorithm: str = "aes-256-gcm"
    key_size: int = 32
    time_cost: int = 3
    memory_cost: int = 65536
    parallelism: int = 4

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> "KeyMaterial":
        """Deserialise from a JSON string."""
        return cls(**json.loads(data))

    @classmethod
    def from_dict(cls, data: dict) -> "KeyMaterial":
        """Deserialise from a dictionary."""
        return cls(**data)


class KeyManager:
    """Creates and manages cryptographic key material.

    All key derivation is delegated to :class:`security.password.PasswordManager`.
    This class is responsible for generating salts, storing key metadata, and
    re-deriving keys on demand.
    """

    def __init__(self) -> None:
        self._pm = PasswordManager()

    def generate_key_material(
        self,
        algorithm: str = "aes-256-gcm",
        key_size: int = 32,
    ) -> KeyMaterial:
        """Create fresh :class:`KeyMaterial` with a new random salt.

        Args:
            algorithm: Encryption algorithm identifier string.
            key_size:  Desired key length in bytes.

        Returns:
            A :class:`KeyMaterial` instance ready for key derivation.
        """
        salt = self._pm.generate_salt()
        pm = self._pm
        return KeyMaterial(
            salt=salt.hex(),
            algorithm=algorithm,
            key_size=key_size,
            time_cost=pm.time_cost,
            memory_cost=pm.memory_cost,
            parallelism=pm.parallelism,
        )

    def derive_key(self, password: str, material: KeyMaterial) -> bytes:
        """Re-derive the encryption key from *password* and *material*.

        Args:
            password: User-supplied password (never stored).
            material: :class:`KeyMaterial` containing the salt and parameters.

        Returns:
            Raw key bytes.
        """
        pm = PasswordManager(
            time_cost=material.time_cost,
            memory_cost=material.memory_cost,
            parallelism=material.parallelism,
            hash_len=material.key_size,
        )
        return pm.derive_key(password, bytes.fromhex(material.salt))

    def derive_seed(self, password: str, material: KeyMaterial) -> int:
        """Derive a deterministic integer seed for pixel permutation.

        Args:
            password: User-supplied password.
            material: :class:`KeyMaterial` for salt lookup.

        Returns:
            Non-negative 64-bit integer seed.
        """
        pm = PasswordManager(
            time_cost=material.time_cost,
            memory_cost=material.memory_cost,
            parallelism=material.parallelism,
            hash_len=material.key_size,
        )
        return pm.derive_seed(password, bytes.fromhex(material.salt))

    def save_metadata(self, material: KeyMaterial, path: str | Path) -> None:
        """Write key metadata (salt + params, no key) to *path*.

        Args:
            material: :class:`KeyMaterial` to persist.
            path:     Destination file path.
        """
        Path(path).write_text(material.to_json(), encoding="utf-8")

    def load_metadata(self, path: str | Path) -> KeyMaterial:
        """Load key metadata from *path*.

        Args:
            path: Path to the JSON metadata file.

        Returns:
            Reconstructed :class:`KeyMaterial`.
        """
        return KeyMaterial.from_json(Path(path).read_text(encoding="utf-8"))


# Module-level singleton.
key_manager = KeyManager()
