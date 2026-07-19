"""
PixelShield – Encryption Pipeline
Orchestrates the full image encryption workflow:
  1. Metadata removal
  2. Optional pixel operations (shuffle, channel rotation, bit rotation, chaos)
  3. Optional noise injection
  4. Optional compression
  5. AES-256 encryption (GCM or CBC) OR hybrid RSA+AES
  6. Integrity hash generation
  7. Output file writing
  8. Optional entropy / histogram / perf reports
"""

from __future__ import annotations

import io
import json
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from core.aes import AESCipher
from core.bit_rotation import BitRotator
from core.channel_rotation import ChannelRotator
from core.chaos import ChaosPixelShuffler
from core.entropy import EntropyAnalyser
from core.histogram import HistogramAnalyser
from core.integrity import IntegrityChecker
from core.metadata import MetadataRemover
from core.pixel_shuffle import PixelShuffler
from security.key_manager import KeyManager, KeyMaterial
from utils.config import config
from utils.helpers import ensure_dir, safe_output_path
from utils.logger import encrypt_logger as log
from utils.perf_report import PerfRecorder


@dataclass
class EncryptionOptions:
    """All user-controlled options for a single encryption run."""

    password: str = ""
    algorithm: str = "aes-256-gcm"
    shuffle: bool = True
    chaos: bool = False
    bit_rotation: bool = False
    noise: bool = False
    entropy: bool = True
    histogram: bool = False
    remove_metadata: bool = True
    verify: bool = True
    output: Optional[str] = None
    verbose: bool = False
    compress: bool = False
    secure_wipe: bool = False
    perf_report: bool = False
    # For hybrid mode: paths to RSA key files (auto-generated when absent).
    rsa_private_key_path: Optional[str] = None
    rsa_public_key_path: Optional[str] = None


@dataclass
class EncryptionResult:
    """Paths and metrics produced by a successful encryption run."""

    encrypted_path: str
    metadata_path: str
    hash_path: str
    entropy: Optional[dict] = None
    histogram_path: Optional[str] = None
    perf_report_path: Optional[str] = None
    elapsed_seconds: float = 0.0
    original_size_bytes: int = 0
    encrypted_size_bytes: int = 0


class ImageEncryptor:
    """Full-pipeline image encryptor.

    Args:
        options: :class:`EncryptionOptions` controlling every aspect of the run.
    """

    def __init__(self, options: EncryptionOptions) -> None:
        self.opts = options
        self._km = KeyManager()
        self._integrity = IntegrityChecker()
        self._entropy = EntropyAnalyser()
        self._histogram = HistogramAnalyser()
        self._metadata = MetadataRemover()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def encrypt(self, image_path: str | Path, out_dir: str | Path = "output") -> EncryptionResult:
        """Encrypt the image at *image_path*.

        Args:
            image_path: Path to the source image.
            out_dir:    Directory where output files are written.

        Returns:
            :class:`EncryptionResult` with paths to all generated files.
        """
        import time
        t0 = time.perf_counter()

        src = Path(image_path)
        ensure_dir(out_dir)

        # Optional performance recorder.
        recorder = PerfRecorder("encrypt", str(src)) if self.opts.perf_report else None
        if recorder:
            recorder.start()

        log.info(f"Starting encryption: {src.name}")

        # 1. Load and optionally strip metadata.
        pil_img = Image.open(src).convert("RGB")
        meta_summary = self._metadata.get_metadata_summary(pil_img)
        if self.opts.remove_metadata:
            pil_img = self._metadata.strip(pil_img)
            log.debug("Metadata stripped.")

        original_array = np.array(pil_img, dtype=np.uint8)
        original_bytes = self._pil_to_bytes(pil_img)
        original_size = len(original_bytes)

        # 2. Derive key material (skip for hybrid mode – no password KDF needed).
        algo_lower = self.opts.algorithm.lower()
        is_hybrid = algo_lower == "hybrid"
        is_chacha = algo_lower == "chacha20"
        material: Optional[KeyMaterial] = None
        key: Optional[bytes] = None
        seed: int = 0

        if not is_hybrid:
            material = self._km.generate_key_material(
                algorithm=self.opts.algorithm,
                key_size=32,
            )
            key = self._km.derive_key(self.opts.password, material)
            seed = self._km.derive_seed(self.opts.password, material)
            log.debug(f"Key derived. Algorithm: {self.opts.algorithm}")
        else:
            # Hybrid: derive seed from a fresh random value (embedded in metadata).
            import os
            seed = int.from_bytes(os.urandom(8), "big")

        # 3. Pixel-space operations.
        arr = original_array.copy()
        ops_applied: list[str] = []

        if self.opts.remove_metadata:
            ops_applied.append("metadata_removal")

        if self.opts.shuffle:
            shuffler = PixelShuffler(seed)
            arr = shuffler.shuffle(arr)
            ops_applied.append("pixel_shuffle")
            log.debug("Pixel shuffle applied.")

        if self.opts.chaos:
            r = config.get("chaos.r", 3.99)
            x0 = config.get("chaos.x0", 0.5)
            chaos = ChaosPixelShuffler(seed=seed, r=r, x0=x0)
            arr = chaos.shuffle(arr)
            ops_applied.append("chaos_shuffle")
            log.debug("Chaos shuffle applied.")

        if arr.shape[2] == 3:
            rotator = ChannelRotator(seed)
            arr = rotator.rotate(arr)
            ops_applied.append("channel_rotation")
            log.debug(f"Channel rotation: {rotator.permutation}")

        if self.opts.bit_rotation:
            amount = config.get("pixel_operations.bit_rotation_amount", 2)
            brot = BitRotator(amount=amount, direction="left")
            arr = brot.rotate(arr)
            ops_applied.append("bit_rotation")
            log.debug(f"Bit rotation applied: {amount} bits left.")

        if self.opts.noise:
            arr = self._inject_noise(arr)
            ops_applied.append("noise_injection")
            log.debug("Noise injected.")

        # 4. Serialize processed array to bytes.
        processed_img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        processed_bytes = self._pil_to_bytes(processed_img)

        # 5. Optional compression.
        if self.opts.compress:
            level = config.get("compression.level", 6)
            processed_bytes = zlib.compress(processed_bytes, level=level)
            ops_applied.append("compression")

        # 6. Integrity hash of original bytes.
        original_hash = self._integrity.hash_bytes(original_bytes)

        # 7. Encrypt.
        aad = self._build_aad(arr.shape, ops_applied)

        if is_hybrid:
            ciphertext, rsa_key_info = self._hybrid_encrypt(processed_bytes, aad, out_dir, src)
            container = self._build_container_hybrid(
                ciphertext=ciphertext,
                shape=original_array.shape,
                ops=ops_applied,
                original_hash=original_hash,
                aad=aad,
                seed=seed,
                rsa_key_info=rsa_key_info,
            )
        elif is_chacha:
            from core.chacha import ChaCha20Cipher
            cc = ChaCha20Cipher(key)
            ciphertext = cc.encrypt(processed_bytes, aad=aad)
            log.debug("ChaCha20-Poly1305 encryption done.")
            container = self._build_container(
                ciphertext=ciphertext,
                shape=original_array.shape,
                material=material,
                ops=ops_applied,
                mode="chacha20",
                original_hash=original_hash,
                aad=aad,
            )
        else:
            mode = self._aes_mode()
            cipher = AESCipher(key)
            ciphertext = cipher.encrypt(processed_bytes, mode=mode, aad=aad)
            log.debug(f"AES encryption done. Mode: {mode}")
            container = self._build_container(
                ciphertext=ciphertext,
                shape=original_array.shape,
                material=material,
                ops=ops_applied,
                mode=mode,
                original_hash=original_hash,
                aad=aad,
            )

        # 8. Determine output paths.
        enc_path = safe_output_path(self.opts.output, src, ".psh", out_dir)
        meta_path = enc_path.with_suffix(".metadata.json")
        hash_path = enc_path.with_suffix(".sha256")

        # 9. Write outputs.
        enc_path.write_bytes(container)
        self._integrity.save_hash(original_hash, hash_path)
        meta_path.write_text(
            json.dumps({
                "source": src.name,
                "algorithm": self.opts.algorithm,
                "ops": ops_applied,
                "shape": list(original_array.shape),
                "key_material": asdict(material) if material else None,
                "source_metadata": meta_summary,
            }, indent=2),
            encoding="utf-8",
        )

        encrypted_size = enc_path.stat().st_size
        log.info(f"Encrypted -> {enc_path} ({encrypted_size} bytes)")

        elapsed = time.perf_counter() - t0
        log.info(f"Encryption complete in {elapsed:.3f}s")

        # 10. Optional analyses.
        entropy_result = None
        if self.opts.entropy:
            entropy_result = self._entropy.compare(original_bytes, ciphertext)
            entropy_path = enc_path.with_suffix(".entropy.txt")
            self._entropy.save_report(
                entropy_result["original"],
                entropy_result["encrypted"],
                entropy_path,
            )

        hist_path = None
        if self.opts.histogram:
            hist_path = str(enc_path.with_suffix(".histogram.png"))
            encrypted_arr = np.frombuffer(ciphertext[:original_array.size], dtype=np.uint8)
            enc_display = np.resize(encrypted_arr, original_array.shape)
            self._histogram.plot_and_save(original_array, enc_display, hist_path)

        # 11. Optional perf report.
        perf_path = None
        if recorder:
            metrics = recorder.stop(
                input_bytes=original_size,
                output_bytes=encrypted_size,
                algorithm=self.opts.algorithm,
                ops_applied=ops_applied,
            )
            perf_path = str(enc_path.with_suffix(".perf.json"))
            recorder.save(metrics, perf_path)

        return EncryptionResult(
            encrypted_path=str(enc_path),
            metadata_path=str(meta_path),
            hash_path=str(hash_path),
            entropy=entropy_result,
            histogram_path=hist_path,
            perf_report_path=perf_path,
            elapsed_seconds=elapsed,
            original_size_bytes=original_size,
            encrypted_size_bytes=encrypted_size,
        )

    # ------------------------------------------------------------------
    # Hybrid helpers
    # ------------------------------------------------------------------

    def _hybrid_encrypt(
        self, plaintext: bytes, aad: bytes, out_dir: str | Path, src: Path
    ) -> tuple[bytes, dict]:
        """Encrypt *plaintext* using hybrid RSA+AES mode.

        Returns (ciphertext_bytes, rsa_key_info_dict).
        """
        from core.hybrid import HybridKeyPair, HybridCipher

        out = Path(out_dir)
        priv_path = Path(self.opts.rsa_private_key_path or (out / f"{src.stem}_private.pem"))
        pub_path  = Path(self.opts.rsa_public_key_path  or (out / f"{src.stem}_public.pem"))

        if priv_path.exists():
            key_pair = HybridKeyPair.load(priv_path)
            log.debug(f"Loaded RSA key from {priv_path}")
        else:
            key_pair = HybridKeyPair.generate()
            key_pair.save(priv_path, pub_path)
            log.info(f"Generated RSA key pair -> {priv_path}, {pub_path}")

        cipher = HybridCipher(key_pair)
        ciphertext = cipher.encrypt(plaintext, aad=aad)
        return ciphertext, {"private_key_path": str(priv_path), "public_key_path": str(pub_path)}

    def _build_container_hybrid(
        self, ciphertext: bytes, shape: tuple, ops: list[str],
        original_hash: str, aad: bytes, seed: int, rsa_key_info: dict,
    ) -> bytes:
        """Pack a hybrid-mode .psh container."""
        header = {
            "version": 1,
            "mode": "hybrid",
            "shape": list(shape),
            "ops": ops,
            "original_hash": original_hash,
            "aad": aad.decode(),
            "seed": seed,
            "rsa_key_info": rsa_key_info,
        }
        header_bytes = json.dumps(header).encode()
        return len(header_bytes).to_bytes(4, "big") + header_bytes + ciphertext

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pil_to_bytes(self, img: Image.Image) -> bytes:
        """Serialise a PIL image to PNG bytes."""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _inject_noise(self, arr: np.ndarray) -> np.ndarray:
        """Add Gaussian noise to *arr*."""
        sigma = config.get("noise.sigma", 5.0)
        noise = np.random.normal(0, sigma, arr.shape).astype(np.int16)
        noisy = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return noisy

    def _aes_mode(self) -> str:
        algo = self.opts.algorithm.lower()
        if "gcm" in algo:
            return "gcm"
        if "chacha" in algo:
            return "chacha20"
        return "cbc"

    @staticmethod
    def _build_aad(shape: tuple, ops: list[str]) -> bytes:
        """Build Additional Authenticated Data for GCM."""
        return json.dumps({"shape": list(shape), "ops": ops}).encode()

    def _build_container(
        self,
        ciphertext: bytes,
        shape: tuple,
        material: KeyMaterial,
        ops: list[str],
        mode: str,
        original_hash: str,
        aad: bytes,
    ) -> bytes:
        """Pack all data into a single .psh container.

        Format::

            [4B header len][header JSON][ciphertext]
        """
        header = {
            "version": 1,
            "shape": list(shape),
            "material": asdict(material),
            "ops": ops,
            "mode": mode,
            "original_hash": original_hash,
            "aad": aad.decode(),
        }
        header_bytes = json.dumps(header).encode()
        length_prefix = len(header_bytes).to_bytes(4, "big")
        return length_prefix + header_bytes + ciphertext
