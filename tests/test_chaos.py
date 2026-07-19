"""Tests for chaotic map module."""

import numpy as np
import pytest

from core.chaos import LogisticMap, ChaosPixelShuffler


class TestLogisticMap:
    def test_generate_length(self):
        lmap = LogisticMap(r=3.99, x0=0.5)
        vals = lmap.generate(100)
        assert len(vals) == 100

    def test_values_in_unit_interval(self):
        lmap = LogisticMap(r=3.99, x0=0.5)
        vals = lmap.generate(1000)
        assert np.all(vals > 0) and np.all(vals < 1)

    def test_invalid_r_raises(self):
        with pytest.raises(ValueError):
            LogisticMap(r=2.0, x0=0.5)

    def test_invalid_x0_raises(self):
        with pytest.raises(ValueError):
            LogisticMap(r=3.99, x0=0.0)

    def test_seed_deterministic(self):
        lmap1 = LogisticMap(r=3.99, x0=0.5)
        lmap1.seed(42)
        v1 = lmap1.generate(50)

        lmap2 = LogisticMap(r=3.99, x0=0.5)
        lmap2.seed(42)
        v2 = lmap2.generate(50)

        np.testing.assert_array_almost_equal(v1, v2)

    def test_permutation_is_valid_permutation(self):
        lmap = LogisticMap()
        perm = lmap.permutation(100)
        assert sorted(perm) == list(range(100))


class TestChaosPixelShuffler:
    def test_roundtrip(self):
        rng = np.random.default_rng(0)
        img = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
        chaos = ChaosPixelShuffler(seed=123)
        restored = chaos.unshuffle(chaos.shuffle(img))
        np.testing.assert_array_equal(restored, img)

    def test_shuffle_differs_from_original(self):
        rng = np.random.default_rng(1)
        img = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
        chaos = ChaosPixelShuffler(seed=456)
        assert not np.array_equal(chaos.shuffle(img), img)
