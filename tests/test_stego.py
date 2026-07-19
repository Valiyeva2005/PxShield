"""Tests for LSB steganography module."""

import os
import pytest
import numpy as np
from PIL import Image
from core.stego import LSBSteganography, _capacity_bytes


@pytest.fixture()
def carrier(tmp_path) -> tuple:
    """Returns (carrier_path, carrier_array) for a 256×256 RGB test image."""
    arr = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    p = tmp_path / "carrier.png"
    Image.fromarray(arr, mode="RGB").save(str(p))
    return p, arr


@pytest.fixture()
def small_carrier(tmp_path) -> object:
    """A very small 8×8 carrier for capacity testing."""
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    p = tmp_path / "small.png"
    Image.fromarray(arr, mode="RGB").save(str(p))
    return p


KEY_32 = os.urandom(32)


class TestCapacity:
    def test_capacity_bytes_formula(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        cap = _capacity_bytes(arr)
        # 256*256*3 bits / 8 = 24576 bytes total – 4 bytes header
        assert cap == 256 * 256 * 3 // 8 - 4

    def test_capacity_method(self, carrier):
        path, _ = carrier
        stego = LSBSteganography(encrypt_payload=False)
        info = stego.capacity(path)
        assert info["width"] == 256
        assert info["height"] == 256
        assert info["capacity_bytes"] > 0
        assert info["capacity_kb"] == round(info["capacity_bytes"] / 1024, 2)


class TestEmbedExtract:
    def test_roundtrip_plaintext(self, carrier, tmp_path):
        path, _ = carrier
        payload = b"Hello, steganography!"
        out = tmp_path / "stego.png"
        stego = LSBSteganography(encrypt_payload=False)
        stego.embed(path, payload, out)
        assert stego.extract(out) == payload

    def test_roundtrip_binary(self, carrier, tmp_path):
        path, _ = carrier
        payload = os.urandom(1024)
        out = tmp_path / "stego_bin.png"
        stego = LSBSteganography(encrypt_payload=False)
        stego.embed(path, payload, out)
        assert stego.extract(out) == payload

    def test_roundtrip_encrypted(self, carrier, tmp_path):
        path, _ = carrier
        payload = b"Super secret message!"
        out = tmp_path / "stego_enc.png"
        stego = LSBSteganography(encrypt_payload=True, key=KEY_32)
        stego.embed(path, payload, out)
        assert stego.extract(out) == payload

    def test_pixel_difference_at_most_one(self, carrier, tmp_path):
        """Embedding changes pixel values by at most ±1."""
        path, original_arr = carrier
        payload = b"A" * 1000
        out = tmp_path / "stego_diff.png"
        stego = LSBSteganography(encrypt_payload=False)
        stego.embed(path, payload, out)
        stego_arr = np.array(Image.open(out))
        diff = np.abs(original_arr.astype(int) - stego_arr.astype(int))
        assert diff.max() <= 1

    def test_carrier_too_small_raises(self, small_carrier, tmp_path):
        payload = b"x" * 10_000  # far too large for 8×8 image
        out = tmp_path / "fail.png"
        stego = LSBSteganography(encrypt_payload=False)
        with pytest.raises(ValueError, match="too large"):
            stego.embed(small_carrier, payload, out)

    def test_output_is_png(self, carrier, tmp_path):
        path, _ = carrier
        out = tmp_path / "stego.png"
        stego = LSBSteganography(encrypt_payload=False)
        stego.embed(path, b"test", out)
        with open(out, "rb") as f:
            magic = f.read(8)
        # PNG magic bytes: \x89PNG\r\n\x1a\n
        assert magic[:4] == b"\x89PNG"

    def test_wrong_key_raises_on_extract(self, carrier, tmp_path):
        path, _ = carrier
        out = tmp_path / "stego.png"
        stego_enc = LSBSteganography(encrypt_payload=True, key=KEY_32)
        stego_enc.embed(path, b"secret", out)

        wrong_key = os.urandom(32)
        stego_bad = LSBSteganography(encrypt_payload=True, key=wrong_key)
        with pytest.raises(Exception):
            stego_bad.extract(out)

    def test_embed_returns_payload_length(self, carrier, tmp_path):
        path, _ = carrier
        payload = b"hello!"
        out = tmp_path / "stego.png"
        stego = LSBSteganography(encrypt_payload=False)
        n = stego.embed(path, payload, out)
        assert n == len(payload)

    def test_empty_payload(self, carrier, tmp_path):
        path, _ = carrier
        out = tmp_path / "stego_empty.png"
        stego = LSBSteganography(encrypt_payload=False)
        stego.embed(path, b"", out)
        assert stego.extract(out) == b""

    def test_key_required_when_encrypt(self):
        with pytest.raises(ValueError):
            LSBSteganography(encrypt_payload=True, key=None)
