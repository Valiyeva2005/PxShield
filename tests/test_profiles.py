"""Tests for configuration profiles module."""

import pytest
from utils.profiles import ProfileManager, BUILTIN_PROFILES


@pytest.fixture()
def manager(tmp_path, monkeypatch) -> ProfileManager:
    """Return an isolated ProfileManager that uses a tmp directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    import utils.profiles as pm_mod
    pm_mod._PROFILES_DIR = tmp_path / ".pixelshield"
    pm_mod._PROFILES_FILE = pm_mod._PROFILES_DIR / "profiles.yaml"
    mgr = ProfileManager.__new__(ProfileManager)
    mgr._user = {}
    return mgr


class TestProfileManager:
    def test_list_includes_builtins(self, manager):
        profiles = manager.list_profiles()
        for name in ("fast", "balanced", "paranoid", "hybrid", "analysis"):
            assert name in profiles

    def test_save_and_retrieve(self, manager):
        manager.save_profile("my_profile", {"algorithm": "aes-256-cbc"}, "test profile")
        p = manager.get("my_profile")
        assert p is not None
        assert p["algorithm"] == "aes-256-cbc"

    def test_user_overrides_builtin(self, manager):
        manager.save_profile("balanced", {"algorithm": "aes-256-cbc"}, "overridden")
        assert manager.get("balanced")["algorithm"] == "aes-256-cbc"

    def test_delete_user_profile(self, manager):
        manager.save_profile("temp", {"algorithm": "aes-256-gcm"})
        assert manager.delete_profile("temp") is True
        assert manager.get("temp") is None

    def test_cannot_delete_builtin(self, manager):
        assert manager.delete_profile("fast") is False

    def test_get_nonexistent_returns_none(self, manager):
        assert manager.get("does_not_exist") is None

    def test_apply_to_options(self, manager):
        result = manager.apply_to_options("paranoid", {})
        assert result["shuffle"] is True
        assert result["chaos"] is True
        assert result["noise"] is True

    def test_apply_to_options_unknown_raises(self, manager):
        with pytest.raises(KeyError):
            manager.apply_to_options("nonexistent_profile", {})

    def test_apply_merges_caller_overrides(self, manager):
        # Caller explicitly sets entropy=False; profile says entropy=True.
        result = manager.apply_to_options("balanced", {"entropy": False})
        assert result["entropy"] is False


class TestBuiltinProfiles:
    def test_all_builtins_have_description(self):
        for name, data in BUILTIN_PROFILES.items():
            assert "description" in data, f"Profile '{name}' missing description"

    def test_all_builtins_have_algorithm(self):
        for name, data in BUILTIN_PROFILES.items():
            assert "algorithm" in data, f"Profile '{name}' missing algorithm"
