#!/usr/bin/env python3
"""
PixelShield – Demonstration Script
Runs the full encrypt → decrypt pipeline programmatically (no CLI required).
Useful for embedding PixelShield in other Python applications.

Usage:
    python3 scripts/demo.py
    python3 scripts/demo.py --help
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path when run from any directory.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def create_demo_image(path: Path, size: int = 128) -> None:
    """Create a synthetic RGB test image at *path*."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, mode="RGB").save(str(path))
    print(f"  ✓ Demo image created: {path} ({size}×{size} px)")


def run_aes_demo(image_path: Path, out_dir: Path, password: str) -> None:
    """Demonstrate AES-256-GCM encrypt → decrypt with all analysis options."""
    from core.encrypt import EncryptionOptions, ImageEncryptor
    from core.decrypt import ImageDecryptor
    from utils.helpers import human_bytes

    print("\n─── AES-256-GCM Encryption Demo ───")
    opts = EncryptionOptions(
        password=password,
        algorithm="aes-256-gcm",
        shuffle=True,
        chaos=False,
        bit_rotation=False,
        noise=False,
        entropy=True,
        histogram=True,
        remove_metadata=True,
        verify=True,
        compress=False,
        perf_report=True,
    )

    encryptor = ImageEncryptor(opts)
    enc = encryptor.encrypt(image_path, out_dir=out_dir)

    print(f"  ✓ Encrypted  : {enc.encrypted_path}")
    print(f"  ✓ Metadata   : {enc.metadata_path}")
    print(f"  ✓ Hash       : {enc.hash_path}")
    print(f"  ✓ Histogram  : {enc.histogram_path}")
    print(f"  ✓ Perf report: {enc.perf_report_path}")
    if enc.entropy:
        print(f"  ✓ Entropy    : {enc.entropy['original']:.4f} → {enc.entropy['encrypted']:.4f} bits/byte")
    print(f"  ✓ Size       : {human_bytes(enc.original_size_bytes)} → {human_bytes(enc.encrypted_size_bytes)}")
    print(f"  ✓ Elapsed    : {enc.elapsed_seconds:.3f}s")

    print("\n─── AES-256-GCM Decryption Demo ───")
    decryptor = ImageDecryptor()
    dec = decryptor.decrypt(enc.encrypted_path, password=password, out_dir=out_dir, verify=True)

    status = "PASSED ✓" if dec.integrity_ok else "FAILED ✗"
    print(f"  ✓ Decrypted  : {dec.decrypted_path}")
    print(f"  ✓ Integrity  : {status}")
    print(f"  ✓ Elapsed    : {dec.elapsed_seconds:.3f}s")


def run_hybrid_demo(image_path: Path, out_dir: Path) -> None:
    """Demonstrate hybrid RSA+AES encrypt → decrypt (no password needed)."""
    from core.encrypt import EncryptionOptions, ImageEncryptor
    from core.decrypt import ImageDecryptor

    print("\n─── Hybrid RSA+AES Encryption Demo ───")
    opts = EncryptionOptions(
        algorithm="hybrid",
        shuffle=True,
        entropy=True,
        histogram=False,
        remove_metadata=True,
        verify=True,
    )

    encryptor = ImageEncryptor(opts)
    enc = encryptor.encrypt(image_path, out_dir=out_dir)

    print(f"  ✓ Encrypted      : {enc.encrypted_path}")
    print(f"  ✓ RSA private key: {out_dir}/{image_path.stem}_private.pem")
    print(f"  ✓ RSA public key : {out_dir}/{image_path.stem}_public.pem")
    if enc.entropy:
        print(f"  ✓ Entropy        : {enc.entropy['original']:.4f} → {enc.entropy['encrypted']:.4f} bits/byte")
    print(f"  ✓ Elapsed        : {enc.elapsed_seconds:.3f}s")

    print("\n─── Hybrid RSA+AES Decryption Demo ───")
    priv_key_path = out_dir / f"{image_path.stem}_private.pem"
    decryptor = ImageDecryptor()
    dec = decryptor.decrypt(
        enc.encrypted_path,
        out_dir=out_dir,
        verify=True,
        rsa_private_key_path=str(priv_key_path),
    )

    status = "PASSED ✓" if dec.integrity_ok else "FAILED ✗"
    print(f"  ✓ Decrypted  : {dec.decrypted_path}")
    print(f"  ✓ Integrity  : {status}")
    print(f"  ✓ Elapsed    : {dec.elapsed_seconds:.3f}s")


def run_paranoid_demo(image_path: Path, out_dir: Path, password: str) -> None:
    """Demonstrate 'paranoid' profile: every option enabled."""
    from core.encrypt import EncryptionOptions, ImageEncryptor
    from core.decrypt import ImageDecryptor
    from utils.profiles import profile_manager

    print("\n─── Paranoid Profile Demo (all options) ───")
    settings = profile_manager.get("paranoid") or {}
    settings.pop("description", None)

    opts = EncryptionOptions(
        password=password,
        **{k: v for k, v in settings.items() if k in EncryptionOptions.__dataclass_fields__},
    )

    encryptor = ImageEncryptor(opts)
    enc = encryptor.encrypt(image_path, out_dir=out_dir)
    print(f"  ✓ Encrypted : {enc.encrypted_path}  ({enc.elapsed_seconds:.3f}s)")
    if enc.entropy:
        print(f"  ✓ Entropy   : {enc.entropy['original']:.4f} → {enc.entropy['encrypted']:.4f} bits/byte")

    decryptor = ImageDecryptor()
    dec = decryptor.decrypt(enc.encrypted_path, password=password, out_dir=out_dir, verify=True)
    status = "PASSED ✓" if dec.integrity_ok else "FAILED ✗"
    print(f"  ✓ Decrypted : {dec.decrypted_path}  Integrity: {status}")


def run_chacha20_demo(image_path: Path, out_dir: Path, password: str) -> None:
    """Demonstrate ChaCha20-Poly1305 encrypt → decrypt."""
    from core.encrypt import EncryptionOptions, ImageEncryptor
    from core.decrypt import ImageDecryptor

    print("\n─── ChaCha20-Poly1305 Encryption Demo ───")
    opts = EncryptionOptions(
        password=password,
        algorithm="chacha20",
        shuffle=True,
        entropy=True,
        remove_metadata=True,
        verify=True,
    )

    encryptor = ImageEncryptor(opts)
    enc = encryptor.encrypt(image_path, out_dir=out_dir)

    print(f"  ✓ Encrypted : {enc.encrypted_path}")
    print(f"  ✓ Algorithm : ChaCha20-Poly1305")
    if enc.entropy:
        print(f"  ✓ Entropy   : {enc.entropy['original']:.4f} → {enc.entropy['encrypted']:.4f} bits/byte")
    print(f"  ✓ Elapsed   : {enc.elapsed_seconds:.3f}s")

    print("\n─── ChaCha20-Poly1305 Decryption Demo ───")
    decryptor = ImageDecryptor()
    dec = decryptor.decrypt(enc.encrypted_path, password=password, out_dir=out_dir, verify=True)

    status = "PASSED ✓" if dec.integrity_ok else "FAILED ✗"
    print(f"  ✓ Decrypted : {dec.decrypted_path}")
    print(f"  ✓ Integrity : {status}")
    print(f"  ✓ Elapsed   : {dec.elapsed_seconds:.3f}s")


def run_stego_demo(image_path: Path, out_dir: Path, password: str) -> None:
    """Demonstrate LSB steganography: hide a secret message then reveal it."""
    from core.stego import LSBSteganography

    print("\n─── LSB Steganography Demo ───")

    # Capacity report.
    stego = LSBSteganography(encrypt_payload=False)
    info = stego.capacity(image_path)
    print(
        f"  ✓ Carrier capacity: {info['capacity_bytes']:,} bytes "
        f"({info['capacity_kb']} KB)  [{info['width']}×{info['height']} px]"
    )

    # Hide a secret message (AES-256-GCM encrypted, password mode).
    secret = b"PixelShield steganography demo — invisible payload!"
    stego_path = out_dir / (image_path.stem + "_stego.png")

    stego_enc = LSBSteganography(encrypt_payload=True, password=password)
    n = stego_enc.embed(image_path, secret, stego_path)
    print(f"  ✓ Payload hidden : {n} bytes inside {stego_path.name}")
    print(f"  ✓ Encrypted with : AES-256-GCM  (password-derived Argon2id key)")

    # Reveal.
    stego_dec = LSBSteganography(encrypt_payload=True, password=password)
    revealed = stego_dec.extract(stego_path)
    status = "PASSED ✓" if revealed == secret else "FAILED ✗"
    print(f"  ✓ Revealed       : {revealed.decode()!r}")
    print(f"  ✓ Roundtrip      : {status}")

    # Also demonstrate plain-text (unencrypted) hiding.
    plain_stego = LSBSteganography(encrypt_payload=False)
    plain_path = out_dir / (image_path.stem + "_stego_plain.png")
    plain_stego.embed(image_path, b"Unencrypted LSB payload", plain_path)
    print(f"  ✓ Plain LSB demo : {plain_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PixelShield – Demonstration Script")
    parser.add_argument("--out-dir", default="output/demo", help="Output directory")
    parser.add_argument("--password", default="DemoPassword123!", help="Demo password")
    parser.add_argument("--image", default=None, help="Custom source image path")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip hybrid demo (slow RSA keygen)")
    parser.add_argument("--skip-stego", action="store_true", help="Skip steganography demo")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Create or use demo image.
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: {image_path} not found.", file=sys.stderr)
            sys.exit(1)
    else:
        image_path = Path("demo/sample.png")
        create_demo_image(image_path)

    print(f"\n{'='*52}")
    print("  PixelShield – Demonstration")
    print(f"  Image: {image_path}  |  Output: {out_dir}")
    print(f"{'='*52}")

    # AES-256-GCM demo.
    run_aes_demo(image_path, out_dir, args.password)

    # ChaCha20-Poly1305 demo.
    run_chacha20_demo(image_path, out_dir, args.password)

    # Hybrid RSA+AES demo.
    if not args.skip_hybrid:
        run_hybrid_demo(image_path, out_dir)

    # Paranoid profile demo.
    run_paranoid_demo(image_path, out_dir, args.password)

    # Steganography demo.
    if not args.skip_stego:
        run_stego_demo(image_path, out_dir, args.password)

    print(f"\n{'='*52}")
    print("  All demos completed successfully.")
    print(f"  Output files: {out_dir}/")
    print(f"{'='*52}\n")


if __name__ == "__main__":
    main()
