"""Tests for entropy calculation module."""

import pytest
from core.entropy import shannon_entropy, EntropyAnalyser


class TestShannonEntropy:
    def test_uniform_bytes_max_entropy(self):
        # Uniformly distributed bytes → entropy ≈ 8.0
        data = bytes(range(256)) * 100
        e = shannon_entropy(data)
        assert 7.9 < e <= 8.0

    def test_constant_bytes_zero_entropy(self):
        data = bytes([42] * 1000)
        assert shannon_entropy(data) == 0.0

    def test_empty_returns_zero(self):
        assert shannon_entropy(b"") == 0.0

    def test_entropy_increases_after_encryption(self):
        import os
        low_entropy = bytes([0, 1]) * 500          # low entropy pattern
        high_entropy = os.urandom(1000)             # high entropy (simulates encryption)
        assert shannon_entropy(high_entropy) > shannon_entropy(low_entropy)


class TestEntropyAnalyser:
    def test_compare_returns_expected_keys(self):
        analyser = EntropyAnalyser()
        result = analyser.compare(b"\x00" * 100, bytes(range(256)) * 4)
        assert set(result.keys()) == {"original", "encrypted", "delta"}

    def test_delta_positive_for_random_encrypted(self):
        import os
        analyser = EntropyAnalyser()
        result = analyser.compare(b"\x00" * 256, os.urandom(256))
        assert result["delta"] > 0

    def test_save_report(self, tmp_path):
        analyser = EntropyAnalyser()
        path = tmp_path / "entropy.txt"
        analyser.save_report(5.5, 7.9, path)
        content = path.read_text()
        assert "5.500000" in content
        assert "7.900000" in content
