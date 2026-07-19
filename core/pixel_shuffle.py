"""
PixelShield – Pixel Shuffle
Deterministically permutes and restores pixel positions using a seeded NumPy RNG.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class PixelShuffler:
    """Shuffles and unshuffles the pixel positions of a NumPy image array.

    The permutation is derived from a seed so that it is fully reversible given
    the same seed.

    Args:
        seed: Non-negative integer seed for the random number generator.
    """

    def __init__(self, seed: int) -> None:
        if seed < 0:
            raise ValueError("Seed must be a non-negative integer.")
        self._seed = seed

    def _make_permutation(self, n_pixels: int) -> NDArray[np.intp]:
        """Generate a reproducible random permutation of *n_pixels* indices.

        Args:
            n_pixels: Total number of pixels.

        Returns:
            Array of shuffled indices.
        """
        rng = np.random.default_rng(self._seed)
        return rng.permutation(n_pixels)

    def shuffle(self, image: NDArray) -> NDArray:
        """Randomly permute the pixels of *image*.

        Args:
            image: NumPy array of shape ``(H, W, C)`` or ``(H, W)``.

        Returns:
            New array with pixels in permuted order (same shape).
        """
        shape = image.shape
        flat = image.reshape(-1, *shape[2:]) if image.ndim == 3 else image.flatten()
        n = flat.shape[0]
        idx = self._make_permutation(n)
        shuffled = flat[idx]
        return shuffled.reshape(shape)

    def unshuffle(self, image: NDArray) -> NDArray:
        """Restore the original pixel order from a shuffled *image*.

        Args:
            image: Shuffled NumPy array of shape ``(H, W, C)`` or ``(H, W)``.

        Returns:
            Array with pixels restored to their original positions.
        """
        shape = image.shape
        flat = image.reshape(-1, *shape[2:]) if image.ndim == 3 else image.flatten()
        n = flat.shape[0]
        idx = self._make_permutation(n)
        # Build the inverse permutation.
        inverse = np.empty_like(idx)
        inverse[idx] = np.arange(n, dtype=idx.dtype)
        restored = flat[inverse]
        return restored.reshape(shape)
