"""
Integration tests: full encrypt → decrypt roundtrip.
"""

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.encrypt import EncryptionOptions, ImageEncryptor
from core.decrypt import ImageDecryptor


PASSWORD = "integration_test_password_secure!"


@pytest.fixture(scope="module")
def sample_image_path(tmp_path_factory) -> Path:
    """Create a small synthetic test image."""
    tmp = tmp_path_factory.mktemp("images")
    path = tmp / "test_image.png"
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
    Image.fromarray(arr, mode="RGB").save(str(path))
    return path


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("output")


def _encrypt(sample_image_path, out_dir, **extra_opts) -> str:
    opts = EncryptionOptions(
        password=PASSWORD,
        algorithm="aes-256-gcm",
        shuffle=True,
        entropy=False,
        histogram=False,
        remove_metadata=True,
        verify=True,
        **extra_opts,
    )
    encryptor = ImageEncryptor(opts)
    result = encryptor.encrypt(sample_image_path, out_dir=out_dir)
    return result.encrypted_path


class TestEncryptDecryptRoundtrip:
    def test_gcm_roundtrip_integrity(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir)
        decryptor = ImageDecryptor()
        result = decryptor.decrypt(enc_path, password=PASSWORD, out_dir=out_dir, verify=True)
        assert result.integrity_ok is True
        assert Path(result.decrypted_path).exists()

    def test_cbc_roundtrip(self, sample_image_path, out_dir):
        opts = EncryptionOptions(
            password=PASSWORD,
            algorithm="aes-256-cbc",
            shuffle=False,
            entropy=False,
            histogram=False,
        )
        encryptor = ImageEncryptor(opts)
        enc_result = encryptor.encrypt(sample_image_path, out_dir=out_dir)
        decryptor = ImageDecryptor()
        dec_result = decryptor.decrypt(enc_result.encrypted_path, password=PASSWORD, out_dir=out_dir)
        assert dec_result.integrity_ok is True

    def test_wrong_password_raises(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir)
        decryptor = ImageDecryptor()
        with pytest.raises(ValueError):
            decryptor.decrypt(enc_path, password="wrong_password_xyz", out_dir=out_dir)

    def test_chaos_shuffle_roundtrip(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir, chaos=True)
        decryptor = ImageDecryptor()
        result = decryptor.decrypt(enc_path, password=PASSWORD, out_dir=out_dir)
        assert result.integrity_ok is True

    def test_bit_rotation_roundtrip(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir, bit_rotation=True)
        decryptor = ImageDecryptor()
        result = decryptor.decrypt(enc_path, password=PASSWORD, out_dir=out_dir)
        assert result.integrity_ok is True

    def test_compression_roundtrip(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir, compress=True)
        decryptor = ImageDecryptor()
        result = decryptor.decrypt(enc_path, password=PASSWORD, out_dir=out_dir)
        assert result.integrity_ok is True

    def test_encrypted_file_is_psh(self, sample_image_path, out_dir):
        enc_path = _encrypt(sample_image_path, out_dir)
        assert enc_path.endswith(".psh")

    def test_output_files_created(self, sample_image_path, out_dir):
        opts = EncryptionOptions(
            password=PASSWORD,
            algorithm="aes-256-gcm",
            entropy=True,
            histogram=False,
        )
        encryptor = ImageEncryptor(opts)
        result = encryptor.encrypt(sample_image_path, out_dir=out_dir)
        assert Path(result.encrypted_path).exists()
        assert Path(result.metadata_path).exists()
        assert Path(result.hash_path).exists()
