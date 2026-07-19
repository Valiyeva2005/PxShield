"""Tests for channel rotation module."""

import numpy as np
import pytest

from core.channel_rotation import ChannelRotator


@pytest.fixture()
def rgb_image() -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)


class TestChannelRotator:
    def test_roundtrip(self, rgb_image):
        rotator = ChannelRotator(seed=42)
        rotated = rotator.rotate(rgb_image)
        restored = rotator.unrotate(rotated)
        np.testing.assert_array_equal(restored, rgb_image)

    def test_same_seed_deterministic(self, rgb_image):
        r1 = ChannelRotator(100).rotate(rgb_image)
        r2 = ChannelRotator(100).rotate(rgb_image)
        np.testing.assert_array_equal(r1, r2)

    def test_non_rgb_raises(self):
        gray = np.zeros((10, 10), dtype=np.uint8)
        rotator = ChannelRotator(seed=1)
        with pytest.raises(ValueError):
            rotator.rotate(gray)

    def test_shape_preserved(self, rgb_image):
        rotator = ChannelRotator(seed=5)
        assert rotator.rotate(rgb_image).shape == rgb_image.shape

    def test_negative_seed_raises(self):
        with pytest.raises(ValueError):
            ChannelRotator(seed=-5)
