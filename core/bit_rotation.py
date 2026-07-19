"""
PixelShield – Bit Rotation
Rotates the bits of every pixel value left or right by a fixed amount.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def _rotate_left(arr: NDArray[np.uint8], n: int) -> NDArray[np.uint8]:
    """Circular left-shift of 8-bit values by *n* positions.

    Args:
        arr: Array of uint8 values.
        n:   Number of bit positions to shift (1-7).

    Returns:
        Array with each element bit-rotated left by *n*.
    """
    n = n % 8
    if n == 0:
        return arr.copy()
    return ((arr.astype(np.uint16) << n) | (arr >> (8 - n))).astype(np.uint8)


def _rotate_right(arr: NDArray[np.uint8], n: int) -> NDArray[np.uint8]:
    """Circular right-shift of 8-bit values by *n* positions.

    Args:
        arr: Array of uint8 values.
        n:   Number of bit positions to shift (1-7).

    Returns:
        Array with each element bit-rotated right by *n*.
    """
    n = n % 8
    if n == 0:
        return arr.copy()
    return ((arr >> n) | (arr.astype(np.uint16) << (8 - n)).astype(np.uint8)).astype(np.uint8)


class BitRotator:
    """Rotates the bits of pixel values and provides the inverse operation.

    Args:
        amount:    Number of bit positions to rotate (1-7).
        direction: ``"left"`` or ``"right"`` (default ``"left"``).
    """

    def __init__(self, amount: int = 2, direction: str = "left") -> None:
        if not 1 <= amount <= 7:
            raise ValueError(f"Rotation amount must be between 1 and 7, got {amount}.")
        if direction not in {"left", "right"}:
            raise ValueError(f"Direction must be 'left' or 'right', got {direction!r}.")
        self._amount = amount
        self._direction = direction

    def rotate(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Apply bit rotation to every pixel channel value in *image*.

        Args:
            image: NumPy array of dtype uint8 (any shape).

        Returns:
            New array with bit-rotated pixel values.
        """
        if image.dtype != np.uint8:
            raise TypeError(f"Expected uint8 array, got {image.dtype}.")
        if self._direction == "left":
            return _rotate_left(image, self._amount)
        return _rotate_right(image, self._amount)

    def unrotate(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Reverse the bit rotation applied by :meth:`rotate`.

        Args:
            image: Bit-rotated uint8 array.

        Returns:
            Array with original bit values restored.
        """
        if image.dtype != np.uint8:
            raise TypeError(f"Expected uint8 array, got {image.dtype}.")
        # Inverse: reverse direction.
        if self._direction == "left":
            return _rotate_right(image, self._amount)
        return _rotate_left(image, self._amount)
