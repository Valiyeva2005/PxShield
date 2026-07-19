"""
PixelShield – Decryption Pipeline
Reverses the full encryption pipeline:
  1. Parse .psh container
  2. AES-256 decryption OR hybrid RSA+AES decryption
  3. Optional decompression
  4. Reverse pixel operations (in reverse order)
  5. Integrity verification
  6. Image reconstruction
"""

from __future__ import annotations

import io
import json
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from core.aes import AESCipher
from core.bit_rotation import BitRotator
from core.channel_rotation import ChannelRotator
from core.chaos import ChaosPixelShuffler
from core.integrity import IntegrityChecker
from core.pixel_shuffle import PixelShuffler
from security.key_manager import KeyManager, KeyMaterial
from utils.helpers import ensure_dir, safe_output_path
from utils.logger import decrypt_logger as log


@dataclass
class DecryptionResult:
    """Paths and verification status produced by a successful decryption run."""

    decrypted_path: str
    integrity_ok: bool
    elapsed_seconds: float = 0.0
    original_hash: str = ""


class ImageDecryptor:
    """Full-pipeline image decryptor.

    Reads a ``.psh`` container, re-derives the key from the password (or loads
    the RSA private key for hybrid mode), and reverses all pixel-space operations.
    """

    def __init__(self) -> None:
        self._km = KeyManager()
        self._integrity = IntegrityChecker()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def decrypt(
        self,
        encrypted_path: str | Path,
        password: str = "",
        output: Optional[str] = None,
        out_dir: str | Path = "output",
        verify: bool = True,
        verbose: bool = False,
        rsa_private_key_path: Optional[str] = None,
    ) -> DecryptionResult:
        """Decrypt the ``.psh`` file at *encrypted_path*.

        Args:
            encrypted_path:       Path to the ``.psh`` file.
            password:             User-supplied password (AES modes).
            output:               Explicit output path (optional).
            out_dir:              Default output directory.
            verify:               Whether to verify integrity after decryption.
            verbose:              Log extra detail when True.
            rsa_private_key_path: Path to RSA private key (hybrid mode).

        Returns:
            :class:`DecryptionResult` describing the outcome.
        """
        import time
        t0 = time.perf_counter()

        src = Path(encrypted_path)
        ensure_dir(out_dir)
        log.info(f"Starting decryption: {src.name}")

        # 1. Parse container.
        raw = src.read_bytes()
        header, ciphertext = self._parse_container(raw)

        shape = tuple(header["shape"])
        ops: list[str] = header["ops"]
        original_hash: str = header.get("original_hash", "")
        aad: bytes = header.get("aad", "").encode()
        mode: str = header.get("mode", "gcm")

        log.debug(f"Container parsed. Ops: {ops}, Mode: {mode}")

        # 2. Decrypt.
        if mode == "hybrid":
            processed_bytes = self._hybrid_decrypt(ciphertext, aad, header, rsa_private_key_path)
        elif mode == "chacha20":
            if not password:
                raise ValueError("Password is required for ChaCha20 decryption.")
            material = KeyMaterial.from_dict(header["material"])
            key = self._km.derive_key(password, material)
            seed = self._km.derive_seed(password, material)
            from core.chacha import ChaCha20Cipher
            try:
                processed_bytes = ChaCha20Cipher(key).decrypt(ciphertext, aad=aad)
            except ValueError as exc:
                raise ValueError(f"ChaCha20 decryption failed: {exc}") from exc
            log.debug("ChaCha20-Poly1305 decryption complete.")
        else:
            if not password:
                raise ValueError("Password is required for AES decryption.")
            material = KeyMaterial.from_dict(header["material"])
            key = self._km.derive_key(password, material)
            seed = self._km.derive_seed(password, material)
            cipher = AESCipher(key)
            try:
                processed_bytes = cipher.decrypt(ciphertext, mode=mode, aad=aad)
            except ValueError as exc:
                raise ValueError(f"Decryption failed: {exc}") from exc
            log.debug("AES decryption complete.")

        # Seed for pixel ops.
        if mode == "hybrid":
            seed = header.get("seed", 0)

        # 3. Optional decompression.
        if "compression" in ops:
            processed_bytes = zlib.decompress(processed_bytes)
            log.debug("Decompressed.")

        # 4. Reconstruct processed image.
        buf = io.BytesIO(processed_bytes)
        processed_img = Image.open(buf)
        processed_img.load()
        arr = np.array(processed_img, dtype=np.uint8)

        # 5. Reverse pixel-space operations (reverse order, excluding metadata/noise).
        if "bit_rotation" in ops:
            from utils.config import config as cfg
            amount = cfg.get("pixel_operations.bit_rotation_amount", 2)
            brot = BitRotator(amount=amount, direction="left")
            arr = brot.unrotate(arr)
            log.debug("Bit rotation reversed.")

        if "channel_rotation" in ops and arr.ndim == 3 and arr.shape[2] == 3:
            rotator = ChannelRotator(seed)
            arr = rotator.unrotate(arr)
            log.debug(f"Channel rotation reversed: {rotator.permutation}")

        if "chaos_shuffle" in ops:
            from utils.config import config as cfg
            r = cfg.get("chaos.r", 3.99)
            x0 = cfg.get("chaos.x0", 0.5)
            chaos = ChaosPixelShuffler(seed=seed, r=r, x0=x0)
            arr = chaos.unshuffle(arr)
            log.debug("Chaos shuffle reversed.")

        if "pixel_shuffle" in ops:
            shuffler = PixelShuffler(seed)
            arr = shuffler.unshuffle(arr)
            log.debug("Pixel shuffle reversed.")

        # 6. Reconstruct final image.
        restored_img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        restored_bytes = self._pil_to_bytes(restored_img)

        # 7. Integrity verification.
        integrity_ok = True
        if verify and original_hash:
            integrity_ok = self._integrity.verify_bytes(original_hash, restored_bytes)
            if integrity_ok:
                log.info("Integrity check PASSED ✓")
            else:
                log.warning("Integrity check FAILED – file may have been tampered with.")

        # 8. Write output.
        out_path = safe_output_path(output, src, ".decrypted.png", out_dir)
        restored_img.save(str(out_path))
        log.info(f"Decrypted -> {out_path}")

        elapsed = time.perf_counter() - t0
        log.info(f"Decryption complete in {elapsed:.3f}s")

        return DecryptionResult(
            decrypted_path=str(out_path),
            integrity_ok=integrity_ok,
            elapsed_seconds=elapsed,
            original_hash=original_hash,
        )

    # ------------------------------------------------------------------
    # Hybrid helpers
    # ------------------------------------------------------------------

    def _hybrid_decrypt(
        self, ciphertext: bytes, aad: bytes, header: dict, rsa_private_key_path: Optional[str]
    ) -> bytes:
        """Decrypt ciphertext produced in hybrid mode."""
        from core.hybrid import HybridKeyPair, HybridCipher

        rsa_info = header.get("rsa_key_info", {})
        key_path = rsa_private_key_path or rsa_info.get("private_key_path")
        if not key_path or not Path(key_path).exists():
            raise FileNotFoundError(
                f"RSA private key not found at '{key_path}'. "
                "Provide --rsa-key for hybrid decryption."
            )
        key_pair = HybridKeyPair.load(key_path)
        cipher = HybridCipher(key_pair)
        return cipher.decrypt(ciphertext, aad=aad)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_container(data: bytes) -> tuple[dict, bytes]:
        """Split a .psh container into header dict and ciphertext bytes."""
        if len(data) < 4:
            raise ValueError("Container is too small to be a valid .psh file.")
        header_len = int.from_bytes(data[:4], "big")
        if len(data) < 4 + header_len:
            raise ValueError("Container header length exceeds file size.")
        header_json = data[4: 4 + header_len]
        ciphertext = data[4 + header_len:]
        header = json.loads(header_json.decode())
        return header, ciphertext

    @staticmethod
    def _pil_to_bytes(img: Image.Image) -> bytes:
        """Serialise a PIL image to PNG bytes."""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
