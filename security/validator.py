"""
PixelShield – Input Validator
Validates user inputs, file paths, and algorithm names before any processing.
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_ALGORITHMS = frozenset({"aes-256-cbc", "aes-256-gcm", "chacha20", "hybrid"})
SUPPORTED_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp",
})
ENCRYPTED_EXTENSION = ".psh"
MIN_PASSWORD_LENGTH = 8


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def validate_input_image(path: str | Path) -> Path:
    """Ensure *path* is an existing, supported image file.

    Args:
        path: Path to the candidate image file.

    Returns:
        Resolved :class:`pathlib.Path`.

    Raises:
        ValidationError: When the path is invalid or unsupported.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise ValidationError(f"Input file does not exist: {p}")
    if not p.is_file():
        raise ValidationError(f"Input path is not a file: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image format '{p.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return p


def validate_encrypted_file(path: str | Path) -> Path:
    """Ensure *path* is an existing *.psh* encrypted file.

    Args:
        path: Path to the encrypted file.

    Returns:
        Resolved :class:`pathlib.Path`.

    Raises:
        ValidationError: When the file is missing or has wrong extension.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise ValidationError(f"Encrypted file does not exist: {p}")
    if p.suffix.lower() != ENCRYPTED_EXTENSION:
        raise ValidationError(
            f"Expected a '{ENCRYPTED_EXTENSION}' file, got '{p.suffix}'."
        )
    return p


def validate_input_directory(path: str | Path) -> Path:
    """Ensure *path* is an existing directory.

    Args:
        path: Path to the directory.

    Returns:
        Resolved :class:`pathlib.Path`.

    Raises:
        ValidationError: When the path is not a directory.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise ValidationError(f"Directory does not exist: {p}")
    if not p.is_dir():
        raise ValidationError(f"Path is not a directory: {p}")
    return p


def validate_password(password: str) -> None:
    """Enforce minimum password strength requirements.

    Args:
        password: Plaintext password supplied by the user.

    Raises:
        ValidationError: When the password does not meet requirements.
    """
    if not password or not password.strip():
        raise ValidationError("Password must not be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )


def validate_algorithm(algorithm: str) -> str:
    """Normalise and validate an algorithm identifier.

    Args:
        algorithm: Algorithm name string (case-insensitive).

    Returns:
        Lower-cased, validated algorithm identifier.

    Raises:
        ValidationError: When the algorithm is not supported.
    """
    normalised = algorithm.lower().strip()
    # Accept short aliases.
    _ALIASES = {"chacha20-poly1305": "chacha20", "chacha": "chacha20"}
    normalised = _ALIASES.get(normalised, normalised)
    if normalised not in SUPPORTED_ALGORITHMS:
        raise ValidationError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Choose from: {', '.join(sorted(SUPPORTED_ALGORITHMS))}."
        )
    return normalised


def collect_images(directory: Path) -> list[Path]:
    """Collect all supported image files within *directory* (non-recursive).

    Args:
        directory: Directory to scan.

    Returns:
        Sorted list of image file paths.
    """
    images = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(images)
