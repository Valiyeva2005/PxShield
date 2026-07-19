"""
PixelShield – Configuration Profiles
Named encryption profiles that bundle algorithm + operation settings.
Profiles can be saved to / loaded from ~/.pixelshield/profiles.yaml.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml

_PROFILES_DIR = Path.home() / ".pixelshield"
_PROFILES_FILE = _PROFILES_DIR / "profiles.yaml"

# ── Built-in profiles ────────────────────────────────────────────────────────

BUILTIN_PROFILES: dict[str, dict] = {
    "fast": {
        "description": "Speed-optimised: AES-256-GCM, no pixel ops.",
        "algorithm": "aes-256-gcm",
        "shuffle": False,
        "chaos": False,
        "bit_rotation": False,
        "noise": False,
        "compress": False,
        "entropy": False,
        "histogram": False,
        "remove_metadata": True,
    },
    "balanced": {
        "description": "Default: AES-256-GCM + pixel shuffle + channel rotation.",
        "algorithm": "aes-256-gcm",
        "shuffle": True,
        "chaos": False,
        "bit_rotation": False,
        "noise": False,
        "compress": False,
        "entropy": True,
        "histogram": False,
        "remove_metadata": True,
    },
    "paranoid": {
        "description": "Maximum security: all pixel ops + chaos + noise + compression.",
        "algorithm": "aes-256-gcm",
        "shuffle": True,
        "chaos": True,
        "bit_rotation": True,
        "noise": True,
        "compress": True,
        "entropy": True,
        "histogram": True,
        "remove_metadata": True,
    },
    "hybrid": {
        "description": "RSA + AES envelope encryption (no password required).",
        "algorithm": "hybrid",
        "shuffle": True,
        "chaos": False,
        "bit_rotation": False,
        "noise": False,
        "compress": False,
        "entropy": True,
        "histogram": False,
        "remove_metadata": True,
    },
    "analysis": {
        "description": "Encrypt + full analysis: entropy, histogram, verbose log.",
        "algorithm": "aes-256-gcm",
        "shuffle": True,
        "chaos": False,
        "bit_rotation": False,
        "noise": False,
        "compress": False,
        "entropy": True,
        "histogram": True,
        "remove_metadata": True,
    },
}


class ProfileManager:
    """Manages named encryption profiles (built-in + user-defined).

    User profiles are stored in ``~/.pixelshield/profiles.yaml`` and
    override built-ins with the same name.
    """

    def __init__(self) -> None:
        self._user: dict[str, dict] = {}
        self._load_user_profiles()

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def _load_user_profiles(self) -> None:
        if _PROFILES_FILE.exists():
            try:
                data = yaml.safe_load(_PROFILES_FILE.read_text()) or {}
                self._user = data.get("profiles", {})
            except Exception:  # noqa: BLE001
                self._user = {}

    def _save_user_profiles(self) -> None:
        _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        _PROFILES_FILE.write_text(
            yaml.dump({"profiles": self._user}, default_flow_style=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_profiles(self) -> dict[str, dict]:
        """Return all profiles (built-in + user), user profiles take precedence."""
        merged = {**BUILTIN_PROFILES, **self._user}
        return merged

    def get(self, name: str) -> dict | None:
        """Return a profile by name, or None if not found."""
        return self._user.get(name) or BUILTIN_PROFILES.get(name)

    def save_profile(self, name: str, settings: dict, description: str = "") -> None:
        """Save or overwrite a user profile.

        Args:
            name:        Profile identifier (no spaces).
            settings:    Dict of encryption settings.
            description: Human-readable description.
        """
        self._user[name] = {"description": description, **settings}
        self._save_user_profiles()

    def delete_profile(self, name: str) -> bool:
        """Delete a user-defined profile by name.

        Args:
            name: Profile name to delete.

        Returns:
            True if deleted, False if it was a built-in or not found.
        """
        if name in BUILTIN_PROFILES:
            return False  # Can't delete built-ins.
        if name in self._user:
            del self._user[name]
            self._save_user_profiles()
            return True
        return False

    def apply_to_options(self, profile_name: str, base_opts: dict) -> dict:
        """Merge profile settings into *base_opts*, returning the merged dict.

        Args:
            profile_name: Name of the profile to apply.
            base_opts:    Existing options dict (profile values fill missing keys).

        Returns:
            Merged options dict.

        Raises:
            KeyError: When *profile_name* is not found.
        """
        profile = self.get(profile_name)
        if profile is None:
            raise KeyError(f"Profile not found: {profile_name!r}")
        merged = dict(profile)
        merged.pop("description", None)
        merged.update({k: v for k, v in base_opts.items() if v is not None})
        return merged


# Module-level singleton.
profile_manager = ProfileManager()
