"""Integration tests for ChaCha20-Poly1305 algorithm in the encryption pipeline."""

import numpy as np
import pytest
from pathlib import Path
from PIL import Image

from core.encrypt import EncryptionOptions, ImageEncryptor
from core.decrypt import ImageDecryptor


@pytest.fixture()
def sample_image(tmp_path) -> Path:
    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    p = tmp_path / "test.png"
    Image.fromarray(arr.astype(np.uint8), mode="RGB").save(str(p))
    return p


@pytest.fixture()
def out_dir(tmp_path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


def _encrypt(image_path, out_dir, password="Password1234!", **kwargs):
    opts = EncryptionOptions(
        password=password,
        algorithm="chacha20",
        entropy=False,
        histogram=False,
        **kwargs,
    )
    return ImageEncryptor(opts).encrypt(image_path, out_dir=out_dir)


def _decrypt(enc_path, out_dir, password="Password1234!"):
    return ImageDecryptor().decrypt(enc_path, password=password, out_dir=out_dir, verify=True)


class TestChaCha20Pipeline:
    def test_chacha20_roundtrip(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir)
        dec = _decrypt(enc.encrypted_path, out_dir)
        assert dec.integrity_ok is True

    def test_chacha20_with_shuffle(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir, shuffle=True)
        dec = _decrypt(enc.encrypted_path, out_dir)
        assert dec.integrity_ok is True

    def test_chacha20_with_chaos(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir, chaos=True)
        dec = _decrypt(enc.encrypted_path, out_dir)
        assert dec.integrity_ok is True

    def test_chacha20_wrong_password_raises(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir)
        with pytest.raises(Exception):
            _decrypt(enc.encrypted_path, out_dir, password="WrongPassword!")

    def test_chacha20_output_is_psh(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir)
        assert enc.encrypted_path.endswith(".psh")

    def test_chacha20_encrypted_differs_from_original(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir)
        enc_bytes = Path(enc.encrypted_path).read_bytes()
        orig_bytes = sample_image.read_bytes()
        assert enc_bytes != orig_bytes

    def test_chacha20_with_compression(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir, compress=True)
        dec = _decrypt(enc.encrypted_path, out_dir)
        assert dec.integrity_ok is True

    def test_chacha20_with_bit_rotation(self, sample_image, out_dir):
        enc = _encrypt(sample_image, out_dir, bit_rotation=True)
        dec = _decrypt(enc.encrypted_path, out_dir)
        assert dec.integrity_ok is True
