"""Tests for ChaCha20-Poly1305 cipher module."""

import os
import pytest
from core.chacha import ChaCha20Cipher

KEY_32 = os.urandom(32)


class TestChaCha20Cipher:
    def test_encrypt_decrypt_roundtrip(self):
        c = ChaCha20Cipher(KEY_32)
        pt = b"Hello, ChaCha20!" * 100
        assert c.decrypt(c.encrypt(pt)) == pt

    def test_encrypt_with_aad(self):
        c = ChaCha20Cipher(KEY_32)
        pt = b"authenticated data"
        aad = b'{"shape":[64,64,3]}'
        assert c.decrypt(c.encrypt(pt, aad=aad), aad=aad) == pt

    def test_wrong_aad_raises(self):
        c = ChaCha20Cipher(KEY_32)
        enc = c.encrypt(b"data", aad=b"correct")
        with pytest.raises(ValueError):
            c.decrypt(enc, aad=b"wrong")

    def test_tamper_detected(self):
        c = ChaCha20Cipher(KEY_32)
        enc = bytearray(c.encrypt(b"secret message"))
        enc[-1] ^= 0xFF
        with pytest.raises(ValueError):
            c.decrypt(bytes(enc))

    def test_wrong_key_raises(self):
        c1 = ChaCha20Cipher(os.urandom(32))
        c2 = ChaCha20Cipher(os.urandom(32))
        enc = c1.encrypt(b"data")
        with pytest.raises(ValueError):
            c2.decrypt(enc)

    def test_invalid_key_length_raises(self):
        with pytest.raises(ValueError):
            ChaCha20Cipher(b"short")

    def test_empty_plaintext(self):
        c = ChaCha20Cipher(KEY_32)
        assert c.decrypt(c.encrypt(b"")) == b""

    def test_large_payload(self):
        c = ChaCha20Cipher(KEY_32)
        pt = os.urandom(1_048_576)  # 1 MB
        assert c.decrypt(c.encrypt(pt)) == pt

    def test_ciphertext_different_each_time(self):
        """Random nonce means two encryptions of the same plaintext differ."""
        c = ChaCha20Cipher(KEY_32)
        pt = b"same plaintext"
        assert c.encrypt(pt) != c.encrypt(pt)

    def test_short_data_raises_on_decrypt(self):
        c = ChaCha20Cipher(KEY_32)
        with pytest.raises(ValueError):
            c.decrypt(b"\x00" * 5)
