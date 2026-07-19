"""
PixelShield – General Helper Utilities
File I/O, secure wiping, timing, and memory/CPU reporting.
"""

from __future__ import annotations

import os
import struct
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psutil


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

@contextmanager
def timer(label: str = "Operation") -> Generator[dict, None, None]:
    """Context manager that measures wall-clock time.

    Yields a dict that is populated with ``"elapsed"`` (float, seconds) on exit.

    Example::

        with timer("AES encrypt") as t:
            do_work()
        print(f"Took {t['elapsed']:.3f}s")
    """
    result: dict = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def ensure_dir(path: str | Path) -> Path:
    """Create *path* and all parents; return the resolved Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_output_path(output: str | Path | None, source: Path, suffix: str, out_dir: str | Path = "output") -> Path:
    """Derive a safe output path.

    Args:
        output:  Explicit output path supplied by the caller (may be None).
        source:  Source file path; used to derive a default name.
        suffix:  File suffix to apply when generating a default name.
        out_dir: Default output directory.

    Returns:
        Resolved output path (parents created on demand).
    """
    if output:
        p = Path(output)
        ensure_dir(p.parent)
        return p
    out = ensure_dir(out_dir) / (source.stem + suffix)
    return out


# ---------------------------------------------------------------------------
# Secure wipe
# ---------------------------------------------------------------------------

def secure_wipe(path: str | Path, passes: int = 3) -> None:
    """Overwrite *path* with random bytes *passes* times then delete it.

    This is a best-effort defence against naive forensic recovery on spinning
    disks.  On SSDs and copy-on-write file systems it offers limited guarantees.

    Args:
        path:   File to wipe.
        passes: Number of overwrite passes (default 3).
    """
    p = Path(path)
    if not p.exists():
        return
    size = p.stat().st_size
    with p.open("r+b") as fh:
        for _ in range(passes):
            fh.seek(0)
            fh.write(os.urandom(size))
            fh.flush()
            os.fsync(fh.fileno())
    p.unlink()


# ---------------------------------------------------------------------------
# System resource snapshot
# ---------------------------------------------------------------------------

def resource_snapshot() -> dict:
    """Return a snapshot of current process resource usage.

    Returns:
        Dict with keys ``cpu_percent``, ``rss_mb``, ``vms_mb``.
    """
    proc = psutil.Process()
    mem = proc.memory_info()
    return {
        "cpu_percent": proc.cpu_percent(interval=0.1),
        "rss_mb": mem.rss / 1_048_576,
        "vms_mb": mem.vms / 1_048_576,
    }


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def human_bytes(n: int) -> str:
    """Return a human-readable byte count string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def pack_uint32(value: int) -> bytes:
    """Pack an unsigned 32-bit integer big-endian."""
    return struct.pack(">I", value)


def unpack_uint32(data: bytes) -> int:
    """Unpack an unsigned 32-bit integer big-endian."""
    (value,) = struct.unpack(">I", data[:4])
    return value
