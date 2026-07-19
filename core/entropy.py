"""
PixelShield – Entropy Calculator
Computes Shannon entropy of image data before and after encryption.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def shannon_entropy(data: bytes | NDArray) -> float:
    """Calculate the Shannon entropy (bits per byte) of *data*.

    Args:
        data: Raw bytes or a NumPy array (flattened to 1-D uint8 values).

    Returns:
        Entropy value in bits per symbol (0.0 – 8.0).
    """
    if isinstance(data, np.ndarray):
        flat = data.flatten().astype(np.uint8)
        byte_data = flat.tobytes()
    else:
        byte_data = data

    if not byte_data:
        return 0.0

    counts = Counter(byte_data)
    total = len(byte_data)
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
        if count > 0
    )
    return entropy


class EntropyAnalyser:
    """Analyses and reports the entropy of original vs. encrypted data.

    Usage::

        analyser = EntropyAnalyser()
        original_entropy = analyser.compute(original_bytes)
        encrypted_entropy = analyser.compute(encrypted_bytes)
        analyser.save_report(original_entropy, encrypted_entropy, "output/entropy.txt")
    """

    def compute(self, data: bytes | NDArray) -> float:
        """Return the Shannon entropy of *data*.

        Args:
            data: Raw bytes or uint8 NumPy array.

        Returns:
            Entropy in bits per byte.
        """
        return shannon_entropy(data)

    def compare(
        self,
        original: bytes | NDArray,
        encrypted: bytes | NDArray,
    ) -> dict[str, float]:
        """Compute entropy for both *original* and *encrypted* data.

        Args:
            original:  Pre-encryption bytes or array.
            encrypted: Post-encryption bytes or array.

        Returns:
            Dict with keys ``"original"``, ``"encrypted"``, and ``"delta"``.
        """
        orig_e = self.compute(original)
        enc_e = self.compute(encrypted)
        return {
            "original": round(orig_e, 6),
            "encrypted": round(enc_e, 6),
            "delta": round(enc_e - orig_e, 6),
        }

    def save_report(
        self,
        original_entropy: float,
        encrypted_entropy: float,
        path: str | Path,
    ) -> None:
        """Write a human-readable entropy report to *path*.

        Args:
            original_entropy:  Entropy of the original image.
            encrypted_entropy: Entropy of the encrypted image.
            path:              Output file path.
        """
        report_lines = [
            "PixelShield – Entropy Analysis Report",
            "=" * 42,
            f"Original image entropy :  {original_entropy:.6f} bits/byte",
            f"Encrypted image entropy:  {encrypted_entropy:.6f} bits/byte",
            f"Delta (improvement)    : +{encrypted_entropy - original_entropy:.6f} bits/byte",
            "",
            "Note: Ideal AES-encrypted data approaches 8.0 bits/byte (maximum entropy).",
        ]
        Path(path).write_text("\n".join(report_lines), encoding="utf-8")


# Module-level singleton.
entropy_analyser = EntropyAnalyser()
