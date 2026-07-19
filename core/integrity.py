"""
PixelShield – Integrity Verification
SHA-256 hashing and hash file I/O for tamper detection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class IntegrityChecker:
    """Generates and verifies SHA-256 hashes for binary data or files.

    Usage::

        checker = IntegrityChecker()
        digest = checker.hash_bytes(raw_image_bytes)
        checker.save_hash(digest, "output/image.sha256")
        checker.verify_file("output/image.sha256", raw_image_bytes)
    """

    ALGORITHM = "sha256"

    def hash_bytes(self, data: bytes) -> str:
        """Compute the SHA-256 digest of *data*.

        Args:
            data: Raw bytes to hash.

        Returns:
            Hex-encoded digest string (64 characters).
        """
        return hashlib.sha256(data).hexdigest()

    def hash_file(self, path: str | Path, chunk_size: int = 65_536) -> str:
        """Compute the SHA-256 digest of a file in streaming chunks.

        Args:
            path:       Path to the file.
            chunk_size: Read chunk size in bytes.

        Returns:
            Hex-encoded digest string.
        """
        h = hashlib.sha256()
        with Path(path).open("rb") as fh:
            while chunk := fh.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    def save_hash(self, digest: str, path: str | Path) -> None:
        """Write *digest* to *path* (one line, no trailing newline).

        Args:
            digest: Hex-encoded SHA-256 digest.
            path:   Destination file path.
        """
        Path(path).write_text(digest, encoding="ascii")

    def load_hash(self, path: str | Path) -> str:
        """Read a stored hex digest from *path*.

        Args:
            path: File containing a hex digest.

        Returns:
            Hex-encoded digest string.
        """
        return Path(path).read_text(encoding="ascii").strip()

    def verify_bytes(self, digest: str, data: bytes) -> bool:
        """Verify that *data* matches the stored *digest*.

        Args:
            digest: Expected hex-encoded SHA-256 digest.
            data:   Bytes to check.

        Returns:
            ``True`` if the digest matches, ``False`` otherwise.
        """
        actual = self.hash_bytes(data)
        return hmac_compare(actual, digest)

    def verify_file(self, hash_path: str | Path, data: bytes) -> bool:
        """Load a stored hash from *hash_path* and verify *data* against it.

        Args:
            hash_path: Path to the ``.sha256`` file.
            data:      Bytes to verify.

        Returns:
            ``True`` if integrity check passes.

        Raises:
            FileNotFoundError: If *hash_path* does not exist.
        """
        expected = self.load_hash(hash_path)
        return self.verify_bytes(expected, data)


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks.

    Args:
        a: First string.
        b: Second string.

    Returns:
        ``True`` if the strings are equal.
    """
    import hmac as _hmac
    return _hmac.compare_digest(a.encode(), b.encode())


# Module-level singleton.
integrity_checker = IntegrityChecker()
