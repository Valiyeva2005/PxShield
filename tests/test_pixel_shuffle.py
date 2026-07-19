"""Tests for pixel shuffle module."""

import numpy as np
import pytest

from core.pixel_shuffle import PixelShuffler


@pytest.fixture()
def sample_image() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)


class TestPixelShuffler:
    def test_roundtrip(self, sample_image):
        shuffler = PixelShuffler(seed=12345)
        shuffled = shuffler.shuffle(sample_image)
        restored = shuffler.unshuffle(shuffled)
        np.testing.assert_array_equal(restored, sample_image)

    def test_shuffle_changes_image(self, sample_image):
        shuffler = PixelShuffler(seed=9999)
        shuffled = shuffler.shuffle(sample_image)
        assert not np.array_equal(shuffled, sample_image)

    def test_different_seeds_produce_different_shuffles(self, sample_image):
        s1 = PixelShuffler(1).shuffle(sample_image)
        s2 = PixelShuffler(2).shuffle(sample_image)
        assert not np.array_equal(s1, s2)

    def test_same_seed_deterministic(self, sample_image):
        s1 = PixelShuffler(777).shuffle(sample_image)
        s2 = PixelShuffler(777).shuffle(sample_image)
        np.testing.assert_array_equal(s1, s2)

    def test_negative_seed_raises(self):
        with pytest.raises(ValueError):
            PixelShuffler(seed=-1)

    def test_grayscale_roundtrip(self):
        rng = np.random.default_rng(0)
        gray = rng.integers(0, 256, size=(32, 32), dtype=np.uint8)
        shuffler = PixelShuffler(seed=100)
        assert np.array_equal(shuffler.unshuffle(shuffler.shuffle(gray)), gray)

    def test_shape_preserved(self, sample_image):
        shuffler = PixelShuffler(seed=42)
        assert shuffler.shuffle(sample_image).shape == sample_image.shape
