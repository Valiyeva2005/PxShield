"""Tests for auto-update checker (offline-safe)."""

import pytest
from unittest.mock import patch, MagicMock
from utils.updater import check_for_update, _parse_version, _current_version


class TestParseVersion:
    def test_basic(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_short(self):
        assert _parse_version("1.0") == (1, 0)

    def test_leading_whitespace(self):
        assert _parse_version("  2.1.0  ") == (2, 1, 0)

    def test_invalid_returns_zeros(self):
        assert _parse_version("not_a_version") == (0, 0, 0)

    def test_comparison_works(self):
        assert _parse_version("2.0.0") > _parse_version("1.9.9")
        assert _parse_version("1.0.0") == _parse_version("1.0.0")


class TestCheckForUpdate:
    def test_offline_returns_gracefully(self):
        """When PyPI is unreachable, the function must not raise."""
        with patch("utils.updater._fetch_latest_version", return_value=None):
            result = check_for_update()
        assert "update_available" in result
        assert result["update_available"] is False
        assert result["latest"] is None

    def test_newer_version_detected(self):
        with patch("utils.updater._current_version", return_value="1.0.0"), \
             patch("utils.updater._fetch_latest_version", return_value="2.0.0"):
            result = check_for_update()
        assert result["update_available"] is True
        assert "2.0.0" in result["message"]

    def test_up_to_date(self):
        with patch("utils.updater._current_version", return_value="1.0.0"), \
             patch("utils.updater._fetch_latest_version", return_value="1.0.0"):
            result = check_for_update()
        assert result["update_available"] is False

    def test_current_version_is_string(self):
        v = _current_version()
        assert isinstance(v, str)
        assert len(v) > 0
