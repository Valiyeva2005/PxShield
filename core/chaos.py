"""
PixelShield – Chaotic Map
Implements the Logistic Map for pseudo-random pixel permutation generation.

x(n+1) = r * x(n) * (1 - x(n))

High sensitivity to initial conditions makes the sequence
unpredictable without knowledge of the seed.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class LogisticMap:
    """Logistic map-based pseudo-random number generator.

    Args:
        r:  Control parameter (must be in (3.57, 4.0] for chaotic behaviour).
        x0: Initial value (must be in (0, 1), exclusive).

    Raises:
        ValueError: When *r* or *x0* are outside valid ranges.
    """

    def __init__(self, r: float = 3.99, x0: float = 0.5) -> None:
        if not (3.57 < r <= 4.0):
            raise ValueError(f"r must be in (3.57, 4.0] for chaos; got {r}.")
        if not (0.0 < x0 < 1.0):
            raise ValueError(f"x0 must be in (0, 1) exclusive; got {x0}.")
        self._r = r
        self._x = x0

    def _seed_from_int(self, seed: int) -> float:
        """Map an integer *seed* to a valid initial x0 value in (0, 1)."""
        # Use the fractional part of seed / prime to stay in (0, 1).
        x0 = (seed * 0.618033988749895) % 1.0  # golden ratio fraction
        # Avoid degenerate fixed points (0 and 1).
        return max(1e-6, min(x0, 1.0 - 1e-6))

    def seed(self, value: int) -> None:
        """Re-initialise the map with an integer *value*.

        Args:
            value: Non-negative integer seed.
        """
        self._x = self._seed_from_int(value)

    def generate(self, n: int, warm_up: int = 100) -> NDArray[np.float64]:
        """Generate *n* chaotic floating-point values in (0, 1).

        Args:
            n:       Number of values to generate.
            warm_up: Iterations to discard before collecting values (avoids
                     transient behaviour near the initial condition).

        Returns:
            1-D float64 array of shape ``(n,)`` with values in ``(0, 1)``.
        """
        x = self._x
        r = self._r
        # Warm-up phase.
        for _ in range(warm_up):
            x = r * x * (1.0 - x)
        # Collect.
        values = np.empty(n, dtype=np.float64)
        for i in range(n):
            x = r * x * (1.0 - x)
            values[i] = x
        self._x = x  # update internal state
        return values

    def permutation(self, n: int, warm_up: int = 100) -> NDArray[np.intp]:
        """Generate a pseudo-random permutation of *n* indices.

        Args:
            n:       Number of elements to permute.
            warm_up: Warm-up iterations (see :meth:`generate`).

        Returns:
            Array of shape ``(n,)`` containing a shuffled index range.
        """
        floats = self.generate(n, warm_up=warm_up)
        return np.argsort(floats).astype(np.intp)


class ChaosPixelShuffler:
    """Pixel shuffler driven by the Logistic Map.

    Args:
        seed:    Integer seed used to initialise the chaotic map.
        r:       Logistic map control parameter.
        x0:      Initial condition (overridden by *seed* when provided).
    """

    def __init__(self, seed: int, r: float = 3.99, x0: float = 0.5) -> None:
        self._seed = seed
        self._r = r
        self._x0 = x0

    def _make_map(self) -> LogisticMap:
        lmap = LogisticMap(r=self._r, x0=self._x0)
        lmap.seed(self._seed)
        return lmap

    def shuffle(self, image: NDArray) -> NDArray:
        """Shuffle pixels using the logistic map permutation.

        Args:
            image: NumPy array of shape ``(H, W, C)`` or ``(H, W)``.

        Returns:
            Array with pixels in chaotic permutation order.
        """
        shape = image.shape
        flat = image.reshape(-1, *shape[2:]) if image.ndim == 3 else image.flatten()
        n = flat.shape[0]
        idx = self._make_map().permutation(n)
        return flat[idx].reshape(shape)

    def unshuffle(self, image: NDArray) -> NDArray:
        """Reverse the chaotic pixel shuffle.

        Args:
            image: Shuffled NumPy array.

        Returns:
            Array with pixels restored to original positions.
        """
        shape = image.shape
        flat = image.reshape(-1, *shape[2:]) if image.ndim == 3 else image.flatten()
        n = flat.shape[0]
        idx = self._make_map().permutation(n)
        inverse = np.empty_like(idx)
        inverse[idx] = np.arange(n, dtype=idx.dtype)
        return flat[inverse].reshape(shape)
