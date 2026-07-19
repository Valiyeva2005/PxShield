"""
PixelShield – Histogram Analysis
Generates and saves RGB histogram plots comparing original and encrypted images.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CLI use
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray


class HistogramAnalyser:
    """Creates side-by-side RGB histogram plots for visual analysis.

    Usage::

        analyser = HistogramAnalyser()
        analyser.plot_and_save(original_array, encrypted_array, "output/histogram.png")
    """

    def _channel_histogram(
        self, image: NDArray[np.uint8], channel: int
    ) -> tuple[NDArray, NDArray]:
        """Compute the histogram for a single RGB channel.

        Args:
            image:   uint8 array of shape (H, W, 3).
            channel: Channel index (0=R, 1=G, 2=B).

        Returns:
            Tuple of (counts, bin_edges) as returned by numpy.histogram.
        """
        counts, edges = np.histogram(image[:, :, channel].flatten(), bins=256, range=(0, 255))
        return counts, edges

    def plot_and_save(
        self,
        original: NDArray[np.uint8],
        encrypted: NDArray[np.uint8],
        path: str | Path,
        dpi: int = 150,
    ) -> None:
        """Plot RGB histograms for *original* and *encrypted* images side-by-side.

        Columns: Original | Encrypted | Difference (absolute).
        Rows:    Red channel | Green channel | Blue channel.

        Args:
            original:  Original uint8 image array (H, W, 3).
            encrypted: Encrypted uint8 image array (H, W, 3).
            path:      Destination path for the PNG file.
            dpi:       Output DPI (default 150).
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        channel_names = ["Red", "Green", "Blue"]
        colours = ["#e74c3c", "#2ecc71", "#3498db"]

        fig, axes = plt.subplots(3, 3, figsize=(15, 10))
        fig.suptitle("PixelShield – Histogram Analysis", fontsize=14, fontweight="bold")
        col_titles = ["Original", "Encrypted", "Difference (|Orig − Enc|)"]

        for ch in range(3):
            orig_counts, edges = self._channel_histogram(original, ch)
            enc_counts, _ = self._channel_histogram(encrypted, ch)
            diff_counts = np.abs(orig_counts.astype(np.int64) - enc_counts.astype(np.int64))
            bins = np.arange(256)

            for col, counts in enumerate([orig_counts, enc_counts, diff_counts]):
                ax = axes[ch, col]
                ax.bar(bins, counts, color=colours[ch], alpha=0.75, width=1.0)
                if ch == 0:
                    ax.set_title(col_titles[col], fontweight="bold")
                ax.set_ylabel(f"{channel_names[ch]} count")
                ax.set_xlabel("Pixel value (0–255)")
                ax.set_xlim(0, 255)
                ax.tick_params(labelsize=8)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(str(path), dpi=dpi, bbox_inches="tight")
        plt.close(fig)

    def flat_histogram(self, image: NDArray[np.uint8]) -> dict[str, NDArray]:
        """Compute per-channel histograms as a dict.

        Args:
            image: uint8 array (H, W, 3).

        Returns:
            Dict mapping ``"R"``, ``"G"``, ``"B"`` to count arrays of length 256.
        """
        return {
            "R": np.histogram(image[:, :, 0].flatten(), bins=256, range=(0, 255))[0],
            "G": np.histogram(image[:, :, 1].flatten(), bins=256, range=(0, 255))[0],
            "B": np.histogram(image[:, :, 2].flatten(), bins=256, range=(0, 255))[0],
        }


# Module-level singleton.
histogram_analyser = HistogramAnalyser()
