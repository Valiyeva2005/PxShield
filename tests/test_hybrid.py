"""Tests for hybrid RSA+AES encryption module."""

import os
import numpy as np
import pytest
from PIL import Image

from core.hybrid import HybridKeyPair, HybridCipher


@pytest.fixture()
def key_pair() -> HybridKeyPair:
    return HybridKeyPair.generate()


@pytest.fixture()
def cipher(key_pair) -> HybridCipher:
    return HybridCipher(key_pair)


class TestHybridKeyPair:
    def test_generate_produces_keys(self):
        kp = HybridKeyPair.generate()
        assert kp.private_key is not None
        assert kp.public_key is not None

    def test_save_and_load(self, tmp_path, key_pair):
        priv = tmp_path / "private.pem"
        pub  = tmp_path / "public.pem"
        key_pair.save(priv, pub)
        loaded = HybridKeyPair.load(priv)
        assert loaded.private_key_pem() == key_pair.private_key_pem()

    def test_pem_export_non_empty(self, key_pair):
        assert len(key_pair.public_key_pem()) > 0
        assert len(key_pair.private_key_pem()) > 0


class TestHybridCipher:
    def test_encrypt_decrypt_roundtrip(self, cipher):
        pt = b"Hello, hybrid encryption!" * 50
        enc = cipher.encrypt(pt)
        assert cipher.decrypt(enc) == pt

    def test_roundtrip_with_aad(self, cipher):
        pt = b"authenticated data test"
        aad = b'{"shape": [64, 64, 3]}'
        enc = cipher.encrypt(pt, aad=aad)
        assert cipher.decrypt(enc, aad=aad) == pt

    def test_wrong_aad_fails(self, cipher):
        enc = cipher.encrypt(b"data", aad=b"correct_aad")
        with pytest.raises(ValueError):
            cipher.decrypt(enc, aad=b"wrong_aad")

    def test_tamper_fails(self, cipher):
        enc = bytearray(cipher.encrypt(b"secret"))
        enc[-1] ^= 0xFF
        with pytest.raises(Exception):
            cipher.decrypt(bytes(enc))

    def test_different_key_pairs_incompatible(self):
        kp1 = HybridKeyPair.generate()
        kp2 = HybridKeyPair.generate()
        enc = HybridCipher(kp1).encrypt(b"data")
        with pytest.raises(Exception):
            HybridCipher(kp2).decrypt(enc)

    def test_large_payload(self, cipher):
        # 1 MB payload
        pt = os.urandom(1_048_576)
        assert cipher.decrypt(cipher.encrypt(pt)) == pt


class TestHybridIntegration:
    """Full encrypt→decrypt roundtrip using the pipeline in hybrid mode."""

    def test_pipeline_hybrid_roundtrip(self, tmp_path):
        from core.encrypt import EncryptionOptions, ImageEncryptor
        from core.decrypt import ImageDecryptor

        # Create test image.
        img_path = tmp_path / "test.png"
        arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        Image.fromarray(arr, mode="RGB").save(str(img_path))

        out_dir = tmp_path / "output"

        opts = EncryptionOptions(
            algorithm="hybrid",
            shuffle=True,
            entropy=False,
            histogram=False,
        )
        encryptor = ImageEncryptor(opts)
        enc_result = encryptor.encrypt(img_path, out_dir=out_dir)

        decryptor = ImageDecryptor()
        dec_result = decryptor.decrypt(
            enc_result.encrypted_path,
            out_dir=out_dir,
            verify=True,
        )
        assert dec_result.integrity_ok is True
        assert dec_result.decrypted_path.endswith(".png")
