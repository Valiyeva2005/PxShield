"""
PixelShield – Configuration Manager
Loads and merges YAML config with runtime overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class Config:
    """Singleton-style configuration container.

    Usage::

        cfg = Config()
        algorithm = cfg.get("encryption.algorithm", default="aes-256-gcm")
    """

    _instance: "Config | None" = None

    def __new__(cls, path: str | Path | None = None) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, Any] = {}
            cls._instance._loaded = False
        return cls._instance

    def load(self, path: str | Path | None = None) -> None:
        """Load configuration from *path* (defaults to bundled config.yaml)."""
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open("r") as fh:
            self._data = yaml.safe_load(fh) or {}
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a nested value using dot-notation keys.

        Args:
            key:     Dot-separated path, e.g. ``"encryption.algorithm"``.
            default: Value returned when the key is absent.

        Returns:
            The resolved value or *default*.
        """
        self._ensure_loaded()
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Override a configuration value at runtime (dot-notation)."""
        self._ensure_loaded()
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        """Return the raw configuration dictionary."""
        self._ensure_loaded()
        return self._data


# Module-level singleton.
config = Config()
