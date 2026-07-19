"""Tests for metadata removal module."""

import io
import struct
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.metadata import MetadataRemover, metadata_remover


def _make_image_with_exif() -> Image.Image:
    """Create a small RGB image and embed a minimal EXIF block."""
    img = Image.fromarray(np.zeros((16, 16, 3), dtype=np.uint8), mode="RGB")
    # PIL's built-in EXIF container (very minimal – just verifies stripping works).
    exif_data = img.getexif()
    exif_data[271] = "TestCamera"  # Make tag
    exif_data[272] = "TestModel"   # Model tag
    exif_data[306] = "2024:01:01 00:00:00"  # DateTime tag
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_data.tobytes())
    buf.seek(0)
    return Image.open(buf)


class TestMetadataRemover:
    def test_strip_removes_exif(self):
        img_with_exif = _make_image_with_exif()
        summary_before = metadata_remover.get_metadata_summary(img_with_exif)
        assert summary_before["has_exif"] is True

        clean = metadata_remover.strip(img_with_exif)
        summary_after = metadata_remover.get_metadata_summary(clean)
        assert summary_after["has_exif"] is False

    def test_strip_preserves_pixel_data(self):
        rng = np.random.default_rng(5)
        arr = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        clean = metadata_remover.strip(img)
        # Pixels should be equivalent after stripping (PNG lossless round-trip).
        np.testing.assert_array_equal(np.array(clean), arr)

    def test_strip_returns_new_image(self):
        img = Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8), mode="RGB")
        clean = metadata_remover.strip(img)
        assert clean is not img

    def test_get_metadata_summary_keys(self):
        img = Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8), mode="RGB")
        summary = metadata_remover.get_metadata_summary(img)
        assert "has_exif" in summary
        assert "exif_key_count" in summary
        assert "mode" in summary

    def test_strip_file(self, tmp_path):
        arr = np.zeros((16, 16, 3), dtype=np.uint8)
        src = tmp_path / "img.png"
        dst = tmp_path / "clean.png"
        Image.fromarray(arr, mode="RGB").save(str(src))
        metadata_remover.strip_file(src, dst)
        assert dst.exists()
        assert dst.stat().st_size > 0

    def test_strip_non_rgb_converts(self):
        # RGBA image should be handled (converted to RGB internally).
        arr = np.zeros((8, 8, 4), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGBA")
        clean = metadata_remover.strip(img)
        assert clean.mode == "RGB"

    def test_strip_fresh_image_has_no_exif(self):
        img = Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8), mode="RGB")
        clean = metadata_remover.strip(img)
        summary = metadata_remover.get_metadata_summary(clean)
        assert summary["has_exif"] is False
