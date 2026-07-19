"""
PixelShield – Auto-Update Checker
Checks PyPI for a newer version of PixelShield and notifies the user.
Works fully offline-safe: any network error is silently ignored.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

_PACKAGE_NAME = "pixelshield"
_PYPI_URL = f"https://pypi.org/pypi/{_PACKAGE_NAME}/json"
_CACHE_FILE = Path.home() / ".pixelshield" / ".update_cache.json"
_CACHE_TTL_SECONDS = 86_400  # 24 hours


def _current_version() -> str:
    """Return the currently installed version string."""
    try:
        from importlib.metadata import version
        return version(_PACKAGE_NAME)
    except Exception:  # noqa: BLE001
        # Fall back to config.yaml version when not installed as a package.
        try:
            from utils.config import config
            return config.get("pixelshield.version", "1.0.0")
        except Exception:  # noqa: BLE001
            return "1.0.0"


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple."""
    try:
        return tuple(int(x) for x in v.strip().split(".")[:3])
    except Exception:  # noqa: BLE001
        return (0, 0, 0)


def _fetch_latest_version() -> Optional[str]:
    """Fetch the latest version string from PyPI, with disk caching."""
    import time, json

    # Read cache.
    if _CACHE_FILE.exists():
        try:
            cache = json.loads(_CACHE_FILE.read_text())
            age = time.time() - cache.get("ts", 0)
            if age < _CACHE_TTL_SECONDS:
                return cache.get("version")
        except Exception:  # noqa: BLE001
            pass

    # Fetch from PyPI (3-second timeout).
    try:
        req = urllib.request.Request(_PYPI_URL, headers={"User-Agent": "pixelshield-updater/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        latest = data["info"]["version"]

        # Write cache.
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps({"ts": time.time(), "version": latest}))
        return latest
    except Exception:  # noqa: BLE001
        return None


def check_for_update() -> dict:
    """Check if a newer version of PixelShield is available.

    Returns:
        Dict with keys:
            - ``current``   (str): Installed version.
            - ``latest``    (str | None): Latest PyPI version, or None if unreachable.
            - ``update_available`` (bool): True when latest > current.
            - ``message``   (str): Human-readable status message.
    """
    current = _current_version()
    latest = _fetch_latest_version()

    if latest is None:
        return {
            "current": current,
            "latest": None,
            "update_available": False,
            "message": "Could not reach PyPI (offline or package not published yet).",
        }

    update_available = _parse_version(latest) > _parse_version(current)
    if update_available:
        message = (
            f"A new version of PixelShield is available: {latest}  "
            f"(you have {current})\n"
            f"  Upgrade: pip install --upgrade pixelshield"
        )
    else:
        message = f"PixelShield {current} is up to date."

    return {
        "current": current,
        "latest": latest,
        "update_available": update_available,
        "message": message,
    }
