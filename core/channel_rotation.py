"""
PixelShield – Channel Rotation
Randomly rotates RGB channels (R→G→B→R or permutations) based on a seed.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


# All permutations of [0, 1, 2] (indices for R, G, B).
_PERMUTATIONS = [
    (0, 1, 2),  # identity – RGB
    (0, 2, 1),  # RBG
    (1, 0, 2),  # GRB
    (1, 2, 0),  # GBR
    (2, 0, 1),  # BRG
    (2, 1, 0),  # BGR
]


class ChannelRotator:
    """Permutes and restores RGB channels of an image using a seeded RNG.

    Args:
        seed: Non-negative integer seed for reproducibility.
    """

    def __init__(self, seed: int) -> None:
        if seed < 0:
            raise ValueError("Seed must be a non-negative integer.")
        self._seed = seed
        self._perm_index = self._pick_permutation_index(seed)

    @staticmethod
    def _pick_permutation_index(seed: int) -> int:
        rng = np.random.default_rng(seed ^ 0xDEADBEEF)
        return int(rng.integers(0, len(_PERMUTATIONS)))

    @property
    def permutation(self) -> tuple[int, int, int]:
        """The chosen channel permutation tuple."""
        return _PERMUTATIONS[self._perm_index]

    def _inverse_permutation(self) -> tuple[int, int, int]:
        """Compute the inverse of the chosen permutation."""
        perm = list(self.permutation)
        inv = [0, 0, 0]
        for dst, src in enumerate(perm):
            inv[src] = dst
        return tuple(inv)  # type: ignore[return-value]

    def rotate(self, image: NDArray) -> NDArray:
        """Apply the channel permutation to *image*.

        Args:
            image: NumPy array of shape ``(H, W, 3)`` with dtype uint8.

        Returns:
            New array with channels permuted.

        Raises:
            ValueError: If the image does not have exactly 3 channels.
        """
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("ChannelRotator requires an image with exactly 3 channels.")
        perm = self.permutation
        return image[:, :, perm].copy()

    def unrotate(self, image: NDArray) -> NDArray:
        """Reverse the channel permutation applied by :meth:`rotate`.

        Args:
            image: NumPy array of shape ``(H, W, 3)`` with permuted channels.

        Returns:
            New array with channels restored to RGB order.
        """
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("ChannelRotator requires an image with exactly 3 channels.")
        inv = self._inverse_permutation()
        return image[:, :, inv].copy()
