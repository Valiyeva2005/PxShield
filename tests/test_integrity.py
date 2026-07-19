"""Tests for integrity checker module."""

import pytest
from core.integrity import IntegrityChecker, integrity_checker


class TestIntegrityChecker:
    def test_hash_bytes_is_64_chars(self):
        digest = integrity_checker.hash_bytes(b"pixelshield")
        assert len(digest) == 64

    def test_same_data_same_hash(self):
        data = b"deterministic"
        assert integrity_checker.hash_bytes(data) == integrity_checker.hash_bytes(data)

    def test_different_data_different_hash(self):
        assert integrity_checker.hash_bytes(b"a") != integrity_checker.hash_bytes(b"b")

    def test_verify_bytes_correct(self):
        data = b"verify me"
        digest = integrity_checker.hash_bytes(data)
        assert integrity_checker.verify_bytes(digest, data) is True

    def test_verify_bytes_wrong(self):
        digest = integrity_checker.hash_bytes(b"original")
        assert integrity_checker.verify_bytes(digest, b"tampered") is False

    def test_save_and_load_hash(self, tmp_path):
        checker = IntegrityChecker()
        digest = checker.hash_bytes(b"test data")
        path = tmp_path / "file.sha256"
        checker.save_hash(digest, path)
        loaded = checker.load_hash(path)
        assert loaded == digest

    def test_verify_file_passes(self, tmp_path):
        checker = IntegrityChecker()
        data = b"integrity test"
        digest = checker.hash_bytes(data)
        path = tmp_path / "test.sha256"
        checker.save_hash(digest, path)
        assert checker.verify_file(path, data) is True

    def test_hash_file(self, tmp_path):
        checker = IntegrityChecker()
        f = tmp_path / "sample.bin"
        f.write_bytes(b"file hash test")
        digest = checker.hash_file(f)
        assert len(digest) == 64
