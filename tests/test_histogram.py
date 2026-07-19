"""Tests for histogram analysis module."""

from pathlib import Path
import numpy as np
import pytest

from core.histogram import HistogramAnalyser, histogram_analyser


@pytest.fixture()
def rgb_image() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)


@pytest.fixture()
def solid_red() -> np.ndarray:
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    img[:, :, 0] = 200  # all pixels red=200
    return img


class TestHistogramAnalyser:
    def test_flat_histogram_returns_three_channels(self, rgb_image):
        hist = histogram_analyser.flat_histogram(rgb_image)
        assert set(hist.keys()) == {"R", "G", "B"}

    def test_flat_histogram_sums_to_pixel_count(self, rgb_image):
        hist = histogram_analyser.flat_histogram(rgb_image)
        n_pixels = rgb_image.shape[0] * rgb_image.shape[1]
        for channel, counts in hist.items():
            assert counts.sum() == n_pixels, f"Channel {channel} sum mismatch"

    def test_flat_histogram_solid_red(self, solid_red):
        hist = histogram_analyser.flat_histogram(solid_red)
        # Red channel: all 1024 pixels at value 200
        assert hist["R"][200] == 32 * 32
        # Green and blue: all at value 0
        assert hist["G"][0] == 32 * 32
        assert hist["B"][0] == 32 * 32

    def test_plot_and_save_creates_file(self, tmp_path, rgb_image):
        rng = np.random.default_rng(0)
        enc_image = rng.integers(0, 256, rgb_image.shape, dtype=np.uint8)
        out = tmp_path / "histogram.png"
        histogram_analyser.plot_and_save(rgb_image, enc_image, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_plot_creates_parent_dirs(self, tmp_path, rgb_image):
        nested = tmp_path / "a" / "b" / "hist.png"
        rng = np.random.default_rng(1)
        enc = rng.integers(0, 256, rgb_image.shape, dtype=np.uint8)
        histogram_analyser.plot_and_save(rgb_image, enc, nested)
        assert nested.exists()

    def test_histogram_bin_count(self, rgb_image):
        hist = histogram_analyser.flat_histogram(rgb_image)
        for counts in hist.values():
            assert len(counts) == 256

    def test_encrypted_image_more_uniform(self):
        """Encrypted (random) images should have more uniform histograms."""
        import os
        analyser = HistogramAnalyser()
        # Solid colour → spike in histogram.
        solid = np.full((64, 64, 3), 50, dtype=np.uint8)
        random_img = np.frombuffer(os.urandom(64 * 64 * 3), dtype=np.uint8).reshape(64, 64, 3)

        solid_hist = analyser.flat_histogram(solid)
        rand_hist = analyser.flat_histogram(random_img)

        # Standard deviation of bin counts: solid should be much higher.
        solid_std = float(np.std(solid_hist["R"].astype(float)))
        rand_std = float(np.std(rand_hist["R"].astype(float)))
        assert solid_std > rand_std
