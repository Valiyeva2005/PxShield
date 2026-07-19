"""
PixelShield – CLI Commands
Defines encrypt, decrypt, batch, benchmark, interactive, profile, and update sub-commands.
"""

from __future__ import annotations

import getpass
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

console = Console()


def _prompt_password(confirm: bool = False, show_strength: bool = True) -> str:
    """Interactively prompt for a password (hidden input) with optional strength meter."""
    password = getpass.getpass("🔑 Password: ")
    if show_strength and confirm:
        from security.strength import strength_meter
        result = strength_meter.evaluate(password)
        console.print(strength_meter.rich_summary(result))
        if not result.is_acceptable:
            console.print("[yellow]⚠  Weak password – consider a stronger one.[/yellow]")
    if confirm:
        confirm_pw = getpass.getpass("🔑 Confirm password: ")
        if password != confirm_pw:
            console.print("[bold red]✗ Passwords do not match.[/bold red]")
            raise typer.Exit(code=1)
    return password


def _print_result_table(title: str, rows: list[tuple[str, str]]) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Field", style="bold white", no_wrap=True)
    table.add_column("Value", style="green")
    for key, val in rows:
        table.add_row(key, str(val))
    console.print(table)


def register_commands(app: typer.Typer) -> None:
    """Attach all sub-commands to *app*."""

    # ------------------------------------------------------------------
    # encrypt
    # ------------------------------------------------------------------

    @app.command("encrypt")
    def encrypt(
        image: str = typer.Argument(..., help="Path to the source image file."),
        password: Optional[str] = typer.Option(None, "--password", "-p", help="Encryption password (prompted if omitted; not used in hybrid mode)."),
        shuffle: bool = typer.Option(True, "--shuffle/--no-shuffle", help="Apply pixel shuffle."),
        chaos: bool = typer.Option(False, "--chaos", help="Apply logistic-map chaos shuffle."),
        bit_rotation: bool = typer.Option(False, "--bit-rotation", help="Apply bit rotation to pixel values."),
        noise: bool = typer.Option(False, "--noise", help="Inject pseudo-random noise before encryption."),
        entropy: bool = typer.Option(True, "--entropy/--no-entropy", help="Compute and save entropy analysis."),
        histogram: bool = typer.Option(False, "--histogram", help="Generate histogram comparison plot."),
        remove_metadata: bool = typer.Option(True, "--remove-metadata/--keep-metadata", help="Strip EXIF metadata."),
        verify: bool = typer.Option(True, "--verify/--no-verify", help="Compute integrity hash."),
        output: Optional[str] = typer.Option(None, "--output", "-o", help="Output .psh file path."),
        out_dir: str = typer.Option("output", "--out-dir", help="Output directory (default: output/)."),
        algorithm: str = typer.Option("aes-256-gcm", "--algorithm", "-a", help="aes-256-gcm | aes-256-cbc | hybrid"),
        compress: bool = typer.Option(False, "--compress", help="Apply lossless compression before encryption."),
        secure_wipe: bool = typer.Option(False, "--wipe", help="Securely wipe the source file after encryption."),
        perf_report: bool = typer.Option(False, "--perf", help="Generate a CPU/memory performance report."),
        profile: Optional[str] = typer.Option(None, "--profile", help="Apply a named encryption profile (fast | balanced | paranoid | hybrid | analysis | custom)."),
        rsa_key: Optional[str] = typer.Option(None, "--rsa-key", help="Path to RSA private key PEM (hybrid mode only; auto-generated if absent)."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
    ) -> None:
        """Encrypt a single image file."""
        from core.encrypt import EncryptionOptions, ImageEncryptor
        from security.validator import validate_input_image, validate_password, validate_algorithm, ValidationError
        from utils.helpers import human_bytes
        from utils.profiles import profile_manager

        try:
            src = validate_input_image(image)
            algo = validate_algorithm(algorithm)
        except ValidationError as exc:
            console.print(f"[bold red]✗ {exc}[/bold red]")
            raise typer.Exit(code=1)

        # Apply named profile if provided.
        if profile:
            try:
                profile_settings = profile_manager.apply_to_options(profile, {})
                algo = profile_settings.get("algorithm", algo)
                shuffle = profile_settings.get("shuffle", shuffle)
                chaos = profile_settings.get("chaos", chaos)
                bit_rotation = profile_settings.get("bit_rotation", bit_rotation)
                noise = profile_settings.get("noise", noise)
                entropy = profile_settings.get("entropy", entropy)
                histogram = profile_settings.get("histogram", histogram)
                remove_metadata = profile_settings.get("remove_metadata", remove_metadata)
                compress = profile_settings.get("compress", compress)
                console.print(f"[dim]Profile '{profile}' applied.[/dim]")
            except KeyError:
                console.print(f"[bold red]✗ Profile not found: {profile!r}[/bold red]")
                raise typer.Exit(code=1)

        is_hybrid = algo == "hybrid"

        if not password and not is_hybrid:
            try:
                password = _prompt_password(confirm=True)
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)

        if not is_hybrid:
            try:
                validate_password(password or "")
            except ValidationError as exc:
                console.print(f"[bold red]✗ {exc}[/bold red]")
                raise typer.Exit(code=1)

        opts = EncryptionOptions(
            password=password or "",
            algorithm=algo,
            shuffle=shuffle,
            chaos=chaos,
            bit_rotation=bit_rotation,
            noise=noise,
            entropy=entropy,
            histogram=histogram,
            remove_metadata=remove_metadata,
            verify=verify,
            output=output,
            verbose=verbose,
            compress=compress,
            secure_wipe=secure_wipe,
            perf_report=perf_report,
            rsa_private_key_path=rsa_key,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Encrypting...", total=None)
            try:
                encryptor = ImageEncryptor(opts)
                result = encryptor.encrypt(src, out_dir=out_dir)
            except Exception as exc:
                console.print(f"[bold red]✗ Encryption failed: {exc}[/bold red]")
                if verbose:
                    console.print_exception()
                raise typer.Exit(code=1)
            finally:
                progress.remove_task(task)

        if secure_wipe:
            from utils.helpers import secure_wipe as do_wipe
            do_wipe(src)
            console.print(f"[yellow]⚠  Source file securely wiped: {src}[/yellow]")

        rows = [
            ("Encrypted file", result.encrypted_path),
            ("Metadata file", result.metadata_path),
            ("Hash file", result.hash_path),
            ("Original size", human_bytes(result.original_size_bytes)),
            ("Encrypted size", human_bytes(result.encrypted_size_bytes)),
            ("Elapsed", f"{result.elapsed_seconds:.3f}s"),
            ("Algorithm", algo),
        ]
        if result.entropy:
            rows += [
                ("Entropy (original)", f"{result.entropy['original']:.4f} bits/byte"),
                ("Entropy (encrypted)", f"{result.entropy['encrypted']:.4f} bits/byte"),
            ]
        if result.histogram_path:
            rows.append(("Histogram", result.histogram_path))
        if result.perf_report_path:
            rows.append(("Perf report", result.perf_report_path))

        _print_result_table("✓ Encryption Complete", rows)

    # ------------------------------------------------------------------
    # decrypt
    # ------------------------------------------------------------------

    @app.command("decrypt")
    def decrypt(
        encrypted_file: str = typer.Argument(..., help="Path to the .psh encrypted file."),
        password: Optional[str] = typer.Option(None, "--password", "-p", help="Decryption password (not used in hybrid mode)."),
        output: Optional[str] = typer.Option(None, "--output", "-o", help="Output image file path."),
        out_dir: str = typer.Option("output", "--out-dir", help="Output directory."),
        verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify integrity after decryption."),
        rsa_key: Optional[str] = typer.Option(None, "--rsa-key", help="Path to RSA private key PEM (hybrid mode)."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
    ) -> None:
        """Decrypt a .psh encrypted image file."""
        from core.decrypt import ImageDecryptor
        from security.validator import validate_encrypted_file, validate_password, ValidationError

        try:
            src = validate_encrypted_file(encrypted_file)
        except ValidationError as exc:
            console.print(f"[bold red]✗ {exc}[/bold red]")
            raise typer.Exit(code=1)

        # Peek at the header to decide if password is needed.
        raw = src.read_bytes()
        header_len = int.from_bytes(raw[:4], "big")
        import json as _json
        header = _json.loads(raw[4:4 + header_len])
        is_hybrid = header.get("mode") == "hybrid"

        if not password and not is_hybrid:
            try:
                password = _prompt_password(confirm=False)
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)

        if not is_hybrid:
            try:
                validate_password(password or "")
            except ValidationError as exc:
                console.print(f"[bold red]✗ {exc}[/bold red]")
                raise typer.Exit(code=1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Decrypting...", total=None)
            try:
                decryptor = ImageDecryptor()
                result = decryptor.decrypt(
                    src,
                    password=password or "",
                    output=output,
                    out_dir=out_dir,
                    verify=verify,
                    verbose=verbose,
                    rsa_private_key_path=rsa_key,
                )
            except Exception as exc:
                console.print(f"[bold red]✗ Decryption failed: {exc}[/bold red]")
                if verbose:
                    console.print_exception()
                raise typer.Exit(code=1)
            finally:
                progress.remove_task(task)

        integrity_label = "[green]PASSED ✓[/green]" if result.integrity_ok else "[red]FAILED ✗[/red]"
        rows = [
            ("Decrypted file", result.decrypted_path),
            ("Integrity check", integrity_label),
            ("SHA-256 (original)", result.original_hash[:16] + "…" if result.original_hash else "N/A"),
            ("Elapsed", f"{result.elapsed_seconds:.3f}s"),
        ]
        _print_result_table("✓ Decryption Complete", rows)

        if not result.integrity_ok:
            console.print(Panel(
                "[bold red]⚠ Integrity verification FAILED.[/bold red]\n"
                "The decrypted image may have been tampered with or the wrong password was used.",
                border_style="red",
            ))
            raise typer.Exit(code=2)

    # ------------------------------------------------------------------
    # batch
    # ------------------------------------------------------------------

    @app.command("batch")
    def batch(
        directory: str = typer.Argument(..., help="Directory containing images to encrypt."),
        password: Optional[str] = typer.Option(None, "--password", "-p"),
        shuffle: bool = typer.Option(True, "--shuffle/--no-shuffle"),
        chaos: bool = typer.Option(False, "--chaos"),
        noise: bool = typer.Option(False, "--noise"),
        entropy: bool = typer.Option(True, "--entropy/--no-entropy"),
        histogram: bool = typer.Option(False, "--histogram"),
        remove_metadata: bool = typer.Option(True, "--remove-metadata/--keep-metadata"),
        out_dir: str = typer.Option("output", "--out-dir"),
        algorithm: str = typer.Option("aes-256-gcm", "--algorithm", "-a"),
        profile: Optional[str] = typer.Option(None, "--profile"),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
    ) -> None:
        """Encrypt all supported images inside a directory."""
        from core.encrypt import EncryptionOptions, ImageEncryptor
        from security.validator import (
            validate_input_directory,
            validate_password,
            validate_algorithm,
            collect_images,
            ValidationError,
        )
        from utils.profiles import profile_manager

        try:
            src_dir = validate_input_directory(directory)
            algo = validate_algorithm(algorithm)
            images = collect_images(src_dir)
        except ValidationError as exc:
            console.print(f"[bold red]✗ {exc}[/bold red]")
            raise typer.Exit(code=1)

        if not images:
            console.print(f"[yellow]No supported images found in {src_dir}.[/yellow]")
            raise typer.Exit(code=0)

        # Apply profile.
        if profile:
            try:
                ps = profile_manager.apply_to_options(profile, {})
                algo = ps.get("algorithm", algo)
                shuffle = ps.get("shuffle", shuffle)
                chaos = ps.get("chaos", chaos)
                noise = ps.get("noise", noise)
                entropy = ps.get("entropy", entropy)
                histogram = ps.get("histogram", histogram)
                remove_metadata = ps.get("remove_metadata", remove_metadata)
            except KeyError:
                console.print(f"[bold red]✗ Profile not found: {profile!r}[/bold red]")
                raise typer.Exit(code=1)

        if not password and algo != "hybrid":
            try:
                password = _prompt_password(confirm=True)
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Cancelled.[/yellow]")
                raise typer.Exit(code=0)

        if algo != "hybrid":
            try:
                validate_password(password or "")
            except ValidationError as exc:
                console.print(f"[bold red]✗ {exc}[/bold red]")
                raise typer.Exit(code=1)

        console.print(f"[cyan]Found {len(images)} image(s) in {src_dir}[/cyan]")

        opts = EncryptionOptions(
            password=password or "",
            algorithm=algo,
            shuffle=shuffle,
            chaos=chaos,
            noise=noise,
            entropy=entropy,
            histogram=histogram,
            remove_metadata=remove_metadata,
            verify=True,
            verbose=verbose,
        )

        success = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            batch_task = progress.add_task("[cyan]Batch encrypting...", total=len(images))
            for img_path in images:
                progress.update(batch_task, description=f"[cyan]{img_path.name}")
                try:
                    encryptor = ImageEncryptor(opts)
                    encryptor.encrypt(img_path, out_dir=out_dir)
                    success += 1
                except Exception as exc:
                    console.print(f"[red]✗ {img_path.name}: {exc}[/red]")
                    failed += 1
                finally:
                    progress.advance(batch_task)

        console.print(Panel(
            f"[green]✓ Success: {success}[/green]   [red]✗ Failed: {failed}[/red]   Total: {len(images)}",
            title="Batch Complete",
            border_style="cyan",
        ))

    # ------------------------------------------------------------------
    # benchmark
    # ------------------------------------------------------------------

    @app.command("benchmark")
    def benchmark(
        image: str = typer.Argument(..., help="Image to use for benchmarking."),
        runs: int = typer.Option(3, "--runs", "-n", help="Number of benchmark runs."),
        algorithm: str = typer.Option("aes-256-gcm", "--algorithm", "-a"),
    ) -> None:
        """Run a performance benchmark on encrypt/decrypt for a given image."""
        from core.encrypt import EncryptionOptions, ImageEncryptor
        from core.decrypt import ImageDecryptor
        from security.validator import validate_input_image, ValidationError
        from utils.helpers import human_bytes, resource_snapshot
        import statistics

        try:
            src = validate_input_image(image)
        except ValidationError as exc:
            console.print(f"[bold red]✗ {exc}[/bold red]")
            raise typer.Exit(code=1)

        password = "benchmark_password_32chars_secure"
        opts = EncryptionOptions(
            password=password,
            algorithm=algorithm,
            shuffle=True,
            entropy=False,
            histogram=False,
        )

        enc_times: list[float] = []
        dec_times: list[float] = []

        console.print(f"[cyan]Running {runs} benchmark run(s) on {src.name} [{algorithm}]...[/cyan]")

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True) as progress:
            task = progress.add_task("Benchmarking...", total=None)
            for i in range(runs):
                progress.update(task, description=f"Run {i+1}/{runs}")
                encryptor = ImageEncryptor(opts)
                enc_result = encryptor.encrypt(src, out_dir="output/.benchmark")
                enc_times.append(enc_result.elapsed_seconds)

                decryptor = ImageDecryptor()
                dec_result = decryptor.decrypt(
                    enc_result.encrypted_path,
                    password=password,
                    out_dir="output/.benchmark",
                )
                dec_times.append(dec_result.elapsed_seconds)

        snap = resource_snapshot()
        rows = [
            ("Image", src.name),
            ("Image size", human_bytes(src.stat().st_size)),
            ("Algorithm", algorithm),
            ("Runs", str(runs)),
            ("Encrypt avg", f"{statistics.mean(enc_times):.3f}s"),
            ("Encrypt min/max", f"{min(enc_times):.3f}s / {max(enc_times):.3f}s"),
            ("Decrypt avg", f"{statistics.mean(dec_times):.3f}s"),
            ("Decrypt min/max", f"{min(dec_times):.3f}s / {max(dec_times):.3f}s"),
            ("RSS memory", f"{snap['rss_mb']:.1f} MB"),
            ("CPU %", f"{snap['cpu_percent']:.1f}%"),
        ]
        _print_result_table("Benchmark Results", rows)

        import shutil
        bench_dir = Path("output/.benchmark")
        if bench_dir.exists():
            shutil.rmtree(bench_dir)

    # ------------------------------------------------------------------
    # stego
    # ------------------------------------------------------------------

    @app.command("stego")
    def stego(
        action: str = typer.Argument(..., help="hide | reveal | capacity"),
        carrier: Optional[str] = typer.Option(None, "--carrier", "-c", help="Carrier image path (PNG/BMP)."),
        payload_file: Optional[str] = typer.Option(None, "--payload", help="File whose contents to hide (hide mode)."),
        payload_text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to hide (alternative to --payload)."),
        output: Optional[str] = typer.Option(None, "--output", "-o", help="Output stego image path (hide mode)."),
        password: Optional[str] = typer.Option(None, "--password", "-p", help="Password for AES encryption of the payload."),
        no_encrypt: bool = typer.Option(False, "--no-encrypt", help="Embed payload without AES encryption (plain LSB)."),
        extract_to: Optional[str] = typer.Option(None, "--extract-to", help="File to write extracted payload (reveal mode)."),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
    ) -> None:
        """LSB steganography – hide or reveal data inside a carrier image.

        \b
        Examples:
          pixelshield stego hide   --carrier photo.png --text "secret" --password "Pass123!"
          pixelshield stego reveal --carrier stego.png --password "Pass123!"
          pixelshield stego capacity --carrier photo.png
        """
        from core.stego import LSBSteganography
        from security.key_manager import KeyManager
        from security.validator import validate_input_image, ValidationError

        # ── Capacity ─────────────────────────────────────────────
        if action == "capacity":
            if not carrier:
                console.print("[red]✗ --carrier is required for capacity.[/red]")
                raise typer.Exit(code=1)
            try:
                p = validate_input_image(carrier)
            except ValidationError as exc:
                console.print(f"[red]✗ {exc}[/red]")
                raise typer.Exit(code=1)
            stego_obj = LSBSteganography(encrypt_payload=False)
            info = stego_obj.capacity(p)
            _print_result_table("Steganographic Capacity", [
                ("Image", str(p.name)),
                ("Dimensions", f"{info['width']} × {info['height']} px"),
                ("Capacity", f"{info['capacity_bytes']:,} bytes  ({info['capacity_kb']} KB)"),
            ])
            return

        # ── Hide ─────────────────────────────────────────────────
        if action == "hide":
            if not carrier:
                console.print("[red]✗ --carrier is required.[/red]")
                raise typer.Exit(code=1)
            try:
                carrier_path = validate_input_image(carrier)
            except ValidationError as exc:
                console.print(f"[red]✗ {exc}[/red]")
                raise typer.Exit(code=1)

            # Collect payload bytes.
            if payload_text is not None:
                payload = payload_text.encode()
            elif payload_file:
                p_file = Path(payload_file)
                if not p_file.is_file():
                    console.print(f"[red]✗ Payload file not found: {payload_file}[/red]")
                    raise typer.Exit(code=1)
                payload = p_file.read_bytes()
            else:
                console.print("[red]✗ Provide --text or --payload.[/red]")
                raise typer.Exit(code=1)

            # Resolve key / password.
            encrypt = not no_encrypt
            stego_password: Optional[str] = None
            if encrypt:
                if not password:
                    try:
                        password = _prompt_password(confirm=True, show_strength=True)
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Cancelled.[/yellow]")
                        raise typer.Exit(code=0)
                stego_password = password

            out_path = output or str(carrier_path.with_name(carrier_path.stem + "_stego.png"))
            stego_obj = LSBSteganography(encrypt_payload=encrypt, password=stego_password)
            try:
                n = stego_obj.embed(carrier_path, payload, out_path)
            except ValueError as exc:
                console.print(f"[red]✗ {exc}[/red]")
                raise typer.Exit(code=1)

            rows = [
                ("Carrier", str(carrier_path)),
                ("Stego image", out_path),
                ("Payload size", f"{n:,} bytes"),
                ("Encrypted", "Yes (AES-256-GCM)" if encrypt else "No (plain LSB)"),
            ]
            _print_result_table("✓ Payload Hidden", rows)

            if encrypt:
                console.print(
                    "[yellow]⚠  Save your password – there is no way to recover the payload without it.[/yellow]"
                )
            return

        # ── Reveal ───────────────────────────────────────────────
        if action == "reveal":
            if not carrier:
                console.print("[red]✗ --carrier is required.[/red]")
                raise typer.Exit(code=1)
            carrier_path = Path(carrier)
            if not carrier_path.exists():
                console.print(f"[red]✗ File not found: {carrier}[/red]")
                raise typer.Exit(code=1)

            encrypt = not no_encrypt
            stego_password: Optional[str] = None
            if encrypt:
                if not password:
                    try:
                        password = _prompt_password(confirm=False, show_strength=False)
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Cancelled.[/yellow]")
                        raise typer.Exit(code=0)
                stego_password = password

            stego_obj = LSBSteganography(encrypt_payload=encrypt, password=stego_password)
            try:
                data = stego_obj.extract(carrier_path)
            except Exception as exc:
                console.print(f"[red]✗ Extraction failed: {exc}[/red]")
                raise typer.Exit(code=1)

            if extract_to:
                Path(extract_to).write_bytes(data)
                console.print(f"[green]✓ Payload written to: {extract_to} ({len(data):,} bytes)[/green]")
            else:
                try:
                    text = data.decode("utf-8")
                    console.print(f"\n[green]Extracted payload ({len(data)} bytes):[/green]\n{text}")
                except UnicodeDecodeError:
                    console.print(
                        f"[yellow]Extracted {len(data):,} bytes (binary). Use --extract-to to save.[/yellow]"
                    )
            return

        console.print(f"[red]✗ Unknown action '{action}'. Use: hide | reveal | capacity[/red]")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # interactive
    # ------------------------------------------------------------------

    @app.command("interactive")
    def interactive_mode() -> None:
        """Launch the guided interactive wizard (no flags needed)."""
        from cli.interactive import run_interactive_mode
        run_interactive_mode()

    # ------------------------------------------------------------------
    # profile
    # ------------------------------------------------------------------

    @app.command("profile")
    def profile_cmd(
        action: str = typer.Argument("list", help="list | save | delete"),
        name: Optional[str] = typer.Option(None, "--name", "-n", help="Profile name."),
        description: Optional[str] = typer.Option(None, "--description", "-d"),
        algorithm: str = typer.Option("aes-256-gcm", "--algorithm", "-a"),
        shuffle: bool = typer.Option(True, "--shuffle/--no-shuffle"),
        chaos: bool = typer.Option(False, "--chaos"),
        bit_rotation: bool = typer.Option(False, "--bit-rotation"),
        noise: bool = typer.Option(False, "--noise"),
        compress: bool = typer.Option(False, "--compress"),
        entropy: bool = typer.Option(True, "--entropy/--no-entropy"),
        histogram: bool = typer.Option(False, "--histogram"),
        remove_metadata: bool = typer.Option(True, "--remove-metadata/--keep-metadata"),
    ) -> None:
        """Manage named encryption profiles.

        \b
        Examples:
          pixelshield profile list
          pixelshield profile save --name my_profile --algorithm aes-256-gcm --chaos
          pixelshield profile delete --name my_profile
        """
        from utils.profiles import profile_manager, BUILTIN_PROFILES
        from security.validator import validate_algorithm, ValidationError

        if action == "list":
            profiles = profile_manager.list_profiles()
            table = Table(title="Encryption Profiles", header_style="bold cyan", border_style="dim")
            table.add_column("Name", style="bold white", no_wrap=True)
            table.add_column("Type", style="dim")
            table.add_column("Algorithm")
            table.add_column("Description", style="dim")
            for pname, data in profiles.items():
                ptype = "[dim]built-in[/dim]" if pname in BUILTIN_PROFILES else "[yellow]user[/yellow]"
                table.add_row(pname, ptype, data.get("algorithm", "—"), data.get("description", ""))
            console.print(table)

        elif action == "save":
            if not name:
                console.print("[red]✗ --name is required for 'save'.[/red]")
                raise typer.Exit(code=1)
            try:
                algo = validate_algorithm(algorithm)
            except ValidationError as exc:
                console.print(f"[red]✗ {exc}[/red]")
                raise typer.Exit(code=1)
            settings = {
                "algorithm": algo,
                "shuffle": shuffle,
                "chaos": chaos,
                "bit_rotation": bit_rotation,
                "noise": noise,
                "compress": compress,
                "entropy": entropy,
                "histogram": histogram,
                "remove_metadata": remove_metadata,
            }
            profile_manager.save_profile(name, settings, description or "")
            console.print(f"[green]✓ Profile '{name}' saved.[/green]")

        elif action == "delete":
            if not name:
                console.print("[red]✗ --name is required for 'delete'.[/red]")
                raise typer.Exit(code=1)
            ok = profile_manager.delete_profile(name)
            if ok:
                console.print(f"[green]✓ Profile '{name}' deleted.[/green]")
            else:
                console.print(f"[red]✗ Cannot delete '{name}' (built-in or not found).[/red]")
                raise typer.Exit(code=1)

        else:
            console.print(f"[red]✗ Unknown action '{action}'. Use: list | save | delete[/red]")
            raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    @app.command("update")
    def update_check() -> None:
        """Check for a newer version of PixelShield on PyPI."""
        from utils.updater import check_for_update

        with Progress(SpinnerColumn(), TextColumn("Checking for updates..."), console=console, transient=True) as prog:
            task = prog.add_task("", total=None)
            info = check_for_update()
            prog.remove_task(task)

        if info["update_available"]:
            console.print(Panel(
                f"[yellow]New version available:[/yellow] [bold]{info['latest']}[/bold]  "
                f"(installed: {info['current']})\n\n"
                f"  [dim]pip install --upgrade pixelshield[/dim]",
                title="⬆  Update Available",
                border_style="yellow",
            ))
        else:
            console.print(Panel(
                f"[green]✓ PixelShield {info['current']} is up to date.[/green]\n"
                f"[dim]{info['message']}[/dim]",
                title="Version Check",
                border_style="green",
            ))
