"""
PixelShield – Interactive Mode
A guided TUI-style wizard for encryption / decryption without memorising flags.
Uses Rich Prompt for styled interactive input.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich import print as rprint

console = Console()


def _section(title: str) -> None:
    console.rule(f"[bold cyan]{title}[/bold cyan]")


def _show_profiles() -> None:
    from utils.profiles import profile_manager
    profiles = profile_manager.list_profiles()
    table = Table(title="Available Profiles", border_style="dim", header_style="bold cyan")
    table.add_column("Name", style="bold white", no_wrap=True)
    table.add_column("Description", style="dim")
    for name, data in profiles.items():
        marker = "[green]●[/green]" if name in ("balanced", "fast", "paranoid", "hybrid", "analysis") else "[yellow]★[/yellow]"
        table.add_row(f"{marker} {name}", data.get("description", ""))
    console.print(table)


def _collect_encrypt_options() -> dict:
    """Interactively collect all encryption options. Returns a dict of kwargs."""
    _section("Image Selection")
    while True:
        image_path = Prompt.ask("  Image file path", default="")
        if Path(image_path).is_file():
            break
        console.print(f"  [red]✗ File not found: {image_path}[/red]")

    _section("Profile")
    _show_profiles()
    use_profile = Confirm.ask("  Apply a named profile?", default=True)
    profile_name: Optional[str] = None
    if use_profile:
        from utils.profiles import profile_manager
        valid = list(profile_manager.list_profiles().keys())
        while True:
            profile_name = Prompt.ask("  Profile name", default="balanced")
            if profile_name in valid:
                break
            console.print(f"  [red]✗ Unknown profile '{profile_name}'. Choose from: {', '.join(valid)}[/red]")

    _section("Password")
    import getpass
    while True:
        password = getpass.getpass("  🔑 Password: ")
        confirm  = getpass.getpass("  🔑 Confirm : ")
        if password == confirm and len(password) >= 8:
            break
        if len(password) < 8:
            console.print("  [red]✗ Password must be at least 8 characters.[/red]")
        else:
            console.print("  [red]✗ Passwords do not match.[/red]")

    _section("Algorithm")
    algorithm = "aes-256-gcm"
    if not profile_name:
        algorithm = Prompt.ask(
            "  Algorithm",
            choices=["aes-256-gcm", "aes-256-cbc", "hybrid"],
            default="aes-256-gcm",
        )

    _section("Pixel Operations")
    if profile_name:
        console.print("  [dim](Pixel operations are set by the selected profile.)[/dim]")
        shuffle = bit_rotation = chaos = noise = None
    else:
        shuffle      = Confirm.ask("  Pixel shuffle?",    default=True)
        chaos        = Confirm.ask("  Chaos shuffle?",    default=False)
        bit_rotation = Confirm.ask("  Bit rotation?",     default=False)
        noise        = Confirm.ask("  Noise injection?",  default=False)

    _section("Analysis & Security")
    entropy         = Confirm.ask("  Compute entropy analysis?",  default=True)
    histogram       = Confirm.ask("  Generate histogram plot?",   default=False)
    remove_metadata = Confirm.ask("  Strip EXIF metadata?",        default=True)
    compress        = Confirm.ask("  Lossless compression first?", default=False)
    secure_wipe     = Confirm.ask("  Securely wipe source file after encryption?", default=False)
    perf_report     = Confirm.ask("  Generate performance report?", default=False)

    _section("Output")
    out_dir = Prompt.ask("  Output directory", default="output")

    opts = {
        "image_path": image_path,
        "password": password,
        "algorithm": algorithm,
        "out_dir": out_dir,
        "entropy": entropy,
        "histogram": histogram,
        "remove_metadata": remove_metadata,
        "compress": compress,
        "secure_wipe": secure_wipe,
        "perf_report": perf_report,
        "profile_name": profile_name,
    }
    if shuffle is not None:
        opts["shuffle"] = shuffle
    if chaos is not None:
        opts["chaos"] = chaos
    if bit_rotation is not None:
        opts["bit_rotation"] = bit_rotation
    if noise is not None:
        opts["noise"] = noise

    return opts


def _collect_decrypt_options() -> dict:
    """Interactively collect all decryption options."""
    _section("Encrypted File")
    while True:
        enc_path = Prompt.ask("  Encrypted .psh file path", default="")
        p = Path(enc_path)
        if p.is_file() and p.suffix == ".psh":
            break
        console.print(f"  [red]✗ Not a valid .psh file: {enc_path}[/red]")

    _section("Password")
    import getpass
    password = getpass.getpass("  🔑 Password: ")

    _section("Output")
    out_dir = Prompt.ask("  Output directory", default="output")
    verify  = Confirm.ask("  Verify integrity after decryption?", default=True)

    return {
        "enc_path": enc_path,
        "password": password,
        "out_dir": out_dir,
        "verify": verify,
    }


def _collect_profile_save_options() -> dict:
    """Interactively collect settings for saving a new profile."""
    _section("Save Profile")
    name        = Prompt.ask("  Profile name (no spaces)")
    description = Prompt.ask("  Description", default="")
    algorithm   = Prompt.ask("  Algorithm", choices=["aes-256-gcm", "aes-256-cbc", "hybrid"], default="aes-256-gcm")
    shuffle      = Confirm.ask("  Pixel shuffle?",  default=True)
    chaos        = Confirm.ask("  Chaos shuffle?",  default=False)
    bit_rotation = Confirm.ask("  Bit rotation?",   default=False)
    noise        = Confirm.ask("  Noise injection?", default=False)
    compress     = Confirm.ask("  Compression?",    default=False)
    entropy      = Confirm.ask("  Entropy analysis?", default=True)
    histogram    = Confirm.ask("  Histogram?",      default=False)
    remove_metadata = Confirm.ask("  Remove metadata?", default=True)

    return {
        "name": name.strip().replace(" ", "_"),
        "description": description,
        "settings": {
            "algorithm": algorithm,
            "shuffle": shuffle,
            "chaos": chaos,
            "bit_rotation": bit_rotation,
            "noise": noise,
            "compress": compress,
            "entropy": entropy,
            "histogram": histogram,
            "remove_metadata": remove_metadata,
        },
    }


def run_interactive_mode() -> None:
    """Launch the PixelShield interactive mode (TUI wizard)."""
    from rich.align import Align

    console.print(Panel(
        Align.center(
            "[bold cyan]PixelShield Interactive Mode[/bold cyan]\n"
            "[dim]A guided wizard for image encryption[/dim]"
        ),
        border_style="cyan",
    ))

    action = Prompt.ask(
        "\n  What would you like to do?",
        choices=["encrypt", "decrypt", "profile", "update", "quit"],
        default="encrypt",
    )

    if action == "quit":
        console.print("[yellow]Goodbye.[/yellow]")
        return

    if action == "update":
        from utils.updater import check_for_update
        info = check_for_update()
        if info["update_available"]:
            console.print(Panel(info["message"], title="Update Available", border_style="yellow"))
        else:
            console.print(f"[green]✓ {info['message']}[/green]")
        return

    if action == "profile":
        sub = Prompt.ask("  Profile action", choices=["list", "save", "delete"], default="list")
        _interactive_profile(sub)
        return

    if action == "encrypt":
        _interactive_encrypt()
    elif action == "decrypt":
        _interactive_decrypt()


def _interactive_encrypt() -> None:
    from core.encrypt import EncryptionOptions, ImageEncryptor
    from utils.profiles import profile_manager
    from utils.perf_report import PerfRecorder
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

    opts_dict = _collect_encrypt_options()

    # Apply profile if selected.
    profile_name = opts_dict.pop("profile_name", None)
    perf = opts_dict.pop("perf_report", False)
    image_path = opts_dict.pop("image_path")
    out_dir = opts_dict.pop("out_dir", "output")

    if profile_name:
        merged = profile_manager.apply_to_options(profile_name, opts_dict)
        opts_dict.update(merged)

    # Build EncryptionOptions.
    enc_opts = EncryptionOptions(
        password=opts_dict["password"],
        algorithm=opts_dict.get("algorithm", "aes-256-gcm"),
        shuffle=opts_dict.get("shuffle", True),
        chaos=opts_dict.get("chaos", False),
        bit_rotation=opts_dict.get("bit_rotation", False),
        noise=opts_dict.get("noise", False),
        entropy=opts_dict.get("entropy", True),
        histogram=opts_dict.get("histogram", False),
        remove_metadata=opts_dict.get("remove_metadata", True),
        compress=opts_dict.get("compress", False),
        secure_wipe=opts_dict.get("secure_wipe", False),
        verify=True,
    )

    recorder = PerfRecorder("encrypt", str(image_path)) if perf else None
    if recorder:
        recorder.start()

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TimeElapsedColumn(), console=console, transient=True) as prog:
        task = prog.add_task("[cyan]Encrypting...", total=None)
        try:
            encryptor = ImageEncryptor(enc_opts)
            result = encryptor.encrypt(image_path, out_dir=out_dir)
        finally:
            prog.remove_task(task)

    if recorder:
        src = Path(image_path)
        metrics = recorder.stop(
            input_bytes=src.stat().st_size,
            output_bytes=Path(result.encrypted_path).stat().st_size,
            algorithm=enc_opts.algorithm,
        )
        perf_path = Path(result.encrypted_path).with_suffix(".perf.json")
        recorder.save(metrics, perf_path)
        console.print(Panel(recorder.format_report(metrics), title="Performance Report", border_style="dim"))

    console.print(Panel(
        f"[green]✓ Encrypted:[/green] {result.encrypted_path}\n"
        f"[green]✓ Hash:[/green]      {result.hash_path}\n"
        f"[green]✓ Metadata:[/green]  {result.metadata_path}\n"
        f"[dim]Elapsed: {result.elapsed_seconds:.3f}s[/dim]",
        title="Encryption Complete",
        border_style="green",
    ))


def _interactive_decrypt() -> None:
    from core.decrypt import ImageDecryptor
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    opts_dict = _collect_decrypt_options()

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), TimeElapsedColumn(), console=console, transient=True) as prog:
        task = prog.add_task("[cyan]Decrypting...", total=None)
        try:
            decryptor = ImageDecryptor()
            result = decryptor.decrypt(
                opts_dict["enc_path"],
                password=opts_dict["password"],
                out_dir=opts_dict["out_dir"],
                verify=opts_dict["verify"],
            )
        finally:
            prog.remove_task(task)

    status = "[green]PASSED ✓[/green]" if result.integrity_ok else "[red]FAILED ✗[/red]"
    console.print(Panel(
        f"[green]✓ Decrypted:[/green] {result.decrypted_path}\n"
        f"Integrity: {status}\n"
        f"[dim]Elapsed: {result.elapsed_seconds:.3f}s[/dim]",
        title="Decryption Complete",
        border_style="green" if result.integrity_ok else "red",
    ))


def _interactive_profile(sub: str) -> None:
    from utils.profiles import profile_manager

    if sub == "list":
        _show_profiles()

    elif sub == "save":
        data = _collect_profile_save_options()
        profile_manager.save_profile(data["name"], data["settings"], data["description"])
        console.print(f"[green]✓ Profile '{data['name']}' saved.[/green]")

    elif sub == "delete":
        _show_profiles()
        name = Prompt.ask("  Profile name to delete")
        ok = profile_manager.delete_profile(name)
        if ok:
            console.print(f"[green]✓ Profile '{name}' deleted.[/green]")
        else:
            console.print(f"[red]✗ Cannot delete '{name}' (built-in or not found).[/red]")
