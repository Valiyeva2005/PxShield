"""
PixelShield – Plugin System
Drop-in plugin support. Place plugin modules in this directory.
Each plugin must expose a ``register(app)`` callable.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


def load_plugins(app) -> list[str]:
    """Discover and load all plugins in the plugins/ directory.

    Args:
        app: Typer application to register plugin commands on.

    Returns:
        List of successfully loaded plugin names.
    """
    loaded: list[str] = []
    plugin_dir = Path(__file__).parent

    for finder, name, _ in pkgutil.iter_modules([str(plugin_dir)]):
        if name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"plugins.{name}")
            if hasattr(module, "register"):
                module.register(app)
                loaded.append(name)
        except Exception as exc:  # noqa: BLE001
            pass  # Log silently; don't crash the CLI if a plugin fails.
    return loaded
