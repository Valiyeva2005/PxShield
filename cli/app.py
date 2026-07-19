"""
PixelShield – CLI Application Entry Point
Bootstraps Typer app, Rich console, ASCII banner, and plugin loading.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cli.commands import register_commands

# ---------------------------------------------------------------------------
# Typer application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="pixelshield",
    help="[bold cyan]PixelShield[/bold cyan] – Advanced Image Encryption CLI",
    add_completion=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)

console = Console()

BANNER = r"""
██████╗ ██╗██╗  ██╗███████╗██╗     ███████╗██╗  ██╗██╗███████╗██╗     ██████╗ 
██╔══██╗██║╚██╗██╔╝██╔════╝██║     ██╔════╝██║  ██║██║██╔════╝██║     ██╔══██╗
██████╔╝██║ ╚███╔╝ █████╗  ██║     ███████╗███████║██║█████╗  ██║     ██║  ██║
██╔═══╝ ██║ ██╔██╗ ██╔══╝  ██║     ╚════██║██╔══██║██║██╔══╝  ██║     ██║  ██║
██║     ██║██╔╝ ██╗███████╗███████╗███████║██║  ██║██║███████╗███████╗██████╔╝
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚═════╝ 
"""


def _print_banner() -> None:
    """Print the ASCII art banner with version information."""
    try:
        from utils.config import config
        version = config.get("pixelshield.version", "1.0.0")
    except Exception:  # noqa: BLE001
        version = "1.0.0"
    banner_text = Text(BANNER, style="bold cyan")
    subtitle = Text(
        f"  Advanced Image Encryption Tool  v{version}  |  AES-256 · Argon2id · RSA · Pixel Cryptography",
        style="dim white",
        justify="center",
    )
    console.print(banner_text)
    console.print(subtitle)
    console.print()


def _load_plugins() -> None:
    """Discover and load enabled plugins from the plugins/ directory."""
    try:
        from utils.config import config
        if not config.get("plugins.enabled", False):
            return
    except Exception:  # noqa: BLE001
        return

    try:
        from plugins import load_plugins
        loaded = load_plugins(app)
        if loaded:
            console.print(f"[dim]Plugins loaded: {', '.join(loaded)}[/dim]")
    except Exception:  # noqa: BLE001
        pass  # Plugin failures must never crash the CLI.


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """PixelShield – Protect your images with multi-layer pixel cryptography."""
    _print_banner()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


# ---------------------------------------------------------------------------
# Register sub-commands and plugins
# ---------------------------------------------------------------------------

register_commands(app)
_load_plugins()
