"""Tests for bit rotation module."""

import numpy as np
import pytest

from core.bit_rotation import BitRotator


@pytest.fixture()
def sample_array() -> np.ndarray:
    return np.array([[0, 1, 127, 128, 255]], dtype=np.uint8)


class TestBitRotator:
    def test_left_roundtrip(self, sample_array):
        brot = BitRotator(amount=3, direction="left")
        assert np.array_equal(brot.unrotate(brot.rotate(sample_array)), sample_array)

    def test_right_roundtrip(self, sample_array):
        brot = BitRotator(amount=5, direction="right")
        assert np.array_equal(brot.unrotate(brot.rotate(sample_array)), sample_array)

    def test_known_value_left(self):
        brot = BitRotator(amount=1, direction="left")
        # 0b00000001 rotated left 1 → 0b00000010 = 2
        inp = np.array([[1]], dtype=np.uint8)
        assert brot.rotate(inp)[0, 0] == 2

    def test_known_value_right(self):
        brot = BitRotator(amount=1, direction="right")
        # 0b00000010 rotated right 1 → 0b00000001 = 1
        inp = np.array([[2]], dtype=np.uint8)
        assert brot.rotate(inp)[0, 0] == 1

    def test_invalid_amount_raises(self):
        with pytest.raises(ValueError):
            BitRotator(amount=0)
        with pytest.raises(ValueError):
            BitRotator(amount=8)

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            BitRotator(amount=2, direction="diagonal")

    def test_wrong_dtype_raises(self):
        brot = BitRotator(amount=2)
        inp = np.array([[1.5, 2.5]], dtype=np.float32)
        with pytest.raises(TypeError):
            brot.rotate(inp)
