"""
PixelShield – Example Plugin
Demonstrates how to extend PixelShield with custom commands.

To activate: place this file in the plugins/ directory.
The plugin is automatically discovered when --plugins is enabled in config.yaml.
"""

from __future__ import annotations

import typer


def register(app: typer.Typer) -> None:
    """Register this plugin's commands on the main Typer app.

    Args:
        app: The root PixelShield Typer application.
    """

    @app.command("example")
    def example_command(
        message: str = typer.Option("Hello from PixelShield plugin!", "--message", "-m"),
    ) -> None:
        """Example plugin command – prints a greeting."""
        typer.echo(message)
