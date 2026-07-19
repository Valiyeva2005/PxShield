"""Tests for AES cipher module."""

import os
import pytest
from core.aes import AESCipher


@pytest.fixture()
def key() -> bytes:
    return os.urandom(32)


@pytest.fixture()
def cipher(key) -> AESCipher:
    return AESCipher(key)


class TestAESGCM:
    def test_roundtrip(self, cipher):
        plaintext = b"Hello, PixelShield!" * 100
        encrypted = cipher.encrypt_gcm(plaintext)
        assert cipher.decrypt_gcm(encrypted) == plaintext

    def test_roundtrip_with_aad(self, cipher):
        plaintext = b"secret image bytes"
        aad = b'{"shape": [100, 100, 3]}'
        enc = cipher.encrypt_gcm(plaintext, aad=aad)
        assert cipher.decrypt_gcm(enc, aad=aad) == plaintext

    def test_tamper_detection(self, cipher):
        encrypted = cipher.encrypt_gcm(b"data")
        tampered = bytearray(encrypted)
        tampered[-1] ^= 0xFF  # Flip last byte
        with pytest.raises(ValueError, match="authentication failed"):
            cipher.decrypt_gcm(bytes(tampered))

    def test_wrong_aad_fails(self, cipher):
        enc = cipher.encrypt_gcm(b"data", aad=b"original_aad")
        with pytest.raises(ValueError):
            cipher.decrypt_gcm(enc, aad=b"wrong_aad")

    def test_empty_plaintext(self, cipher):
        enc = cipher.encrypt_gcm(b"")
        assert cipher.decrypt_gcm(enc) == b""


class TestAESCBC:
    def test_roundtrip(self, cipher):
        plaintext = b"Block cipher test data" * 10
        encrypted = cipher.encrypt_cbc(plaintext)
        assert cipher.decrypt_cbc(encrypted) == plaintext

    def test_iv_is_random(self, cipher):
        enc1 = cipher.encrypt_cbc(b"same plaintext")
        enc2 = cipher.encrypt_cbc(b"same plaintext")
        assert enc1[:16] != enc2[:16], "IVs should be random"

    def test_different_keys_produce_different_ciphertext(self):
        key1, key2 = os.urandom(32), os.urandom(32)
        c1, c2 = AESCipher(key1), AESCipher(key2)
        pt = b"test plaintext data"
        assert c1.encrypt_cbc(pt) != c2.encrypt_cbc(pt)


class TestAESDispatch:
    def test_encrypt_decrypt_gcm_dispatch(self, cipher):
        pt = b"dispatch test"
        enc = cipher.encrypt(pt, mode="gcm")
        assert cipher.decrypt(enc, mode="gcm") == pt

    def test_encrypt_decrypt_cbc_dispatch(self, cipher):
        pt = b"cbc dispatch test"
        enc = cipher.encrypt(pt, mode="cbc")
        assert cipher.decrypt(enc, mode="cbc") == pt

    def test_invalid_mode_raises(self, cipher):
        with pytest.raises(ValueError):
            cipher.encrypt(b"data", mode="ecb")

    def test_wrong_key_length_raises(self):
        with pytest.raises(ValueError):
            AESCipher(b"short")
