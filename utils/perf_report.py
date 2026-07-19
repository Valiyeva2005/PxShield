"""
PixelShield – Performance Report Generator
Records CPU time, wall time, and memory usage for encryption/decryption runs
and writes structured reports to disk.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import psutil


@dataclass
class OperationMetrics:
    """Metrics captured for a single encrypt or decrypt operation."""

    operation: str                  # "encrypt" | "decrypt"
    source_file: str
    elapsed_wall_s: float = 0.0
    cpu_time_user_s: float = 0.0
    cpu_time_sys_s: float = 0.0
    rss_before_mb: float = 0.0
    rss_after_mb: float = 0.0
    rss_delta_mb: float = 0.0
    input_bytes: int = 0
    output_bytes: int = 0
    throughput_mbps: float = 0.0    # MB/s (based on input size / wall time)
    algorithm: str = ""
    ops_applied: list[str] = field(default_factory=list)
    timestamp: str = ""


class PerfRecorder:
    """Context-manager-style recorder for operation performance.

    Usage::

        recorder = PerfRecorder("encrypt", "photo.png")
        recorder.start()
        do_work()
        metrics = recorder.stop(input_bytes=1_000_000, output_bytes=1_050_000)
        recorder.save(metrics, "output/perf_report.json")
    """

    def __init__(self, operation: str, source_file: str) -> None:
        self._operation = operation
        self._source = source_file
        self._proc = psutil.Process()
        self._t_start: float = 0.0
        self._cpu_start: Optional[psutil._common.pcputimes] = None
        self._mem_before: float = 0.0

    def start(self) -> None:
        """Begin recording."""
        self._t_start = time.perf_counter()
        self._cpu_start = self._proc.cpu_times()
        self._mem_before = self._proc.memory_info().rss / 1_048_576

    def stop(
        self,
        input_bytes: int = 0,
        output_bytes: int = 0,
        algorithm: str = "",
        ops_applied: Optional[list[str]] = None,
    ) -> OperationMetrics:
        """Finish recording and return an :class:`OperationMetrics` instance.

        Args:
            input_bytes:  Size of the source data in bytes.
            output_bytes: Size of the output data in bytes.
            algorithm:    Algorithm name used.
            ops_applied:  List of pixel operations applied.

        Returns:
            Populated :class:`OperationMetrics`.
        """
        elapsed = time.perf_counter() - self._t_start
        cpu_end = self._proc.cpu_times()
        mem_after = self._proc.memory_info().rss / 1_048_576

        user_delta = cpu_end.user - (self._cpu_start.user if self._cpu_start else 0)
        sys_delta = cpu_end.system - (self._cpu_start.system if self._cpu_start else 0)
        rss_delta = mem_after - self._mem_before
        throughput = (input_bytes / 1_048_576) / elapsed if elapsed > 0 else 0.0

        return OperationMetrics(
            operation=self._operation,
            source_file=self._source,
            elapsed_wall_s=round(elapsed, 4),
            cpu_time_user_s=round(user_delta, 4),
            cpu_time_sys_s=round(sys_delta, 4),
            rss_before_mb=round(self._mem_before, 2),
            rss_after_mb=round(mem_after, 2),
            rss_delta_mb=round(rss_delta, 2),
            input_bytes=input_bytes,
            output_bytes=output_bytes,
            throughput_mbps=round(throughput, 3),
            algorithm=algorithm,
            ops_applied=ops_applied or [],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def save(self, metrics: OperationMetrics, path: str | Path) -> None:
        """Write *metrics* as a JSON file to *path*.

        Args:
            metrics: :class:`OperationMetrics` to serialise.
            path:    Output file path.
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(asdict(metrics), indent=2), encoding="utf-8"
        )

    def format_report(self, metrics: OperationMetrics) -> str:
        """Return a human-readable multi-line report string.

        Args:
            metrics: Metrics to format.

        Returns:
            Formatted report string.
        """
        lines = [
            "PixelShield – Performance Report",
            "=" * 42,
            f"Operation      : {metrics.operation}",
            f"Source file    : {metrics.source_file}",
            f"Timestamp      : {metrics.timestamp}",
            f"Algorithm      : {metrics.algorithm}",
            f"Operations     : {', '.join(metrics.ops_applied) or 'none'}",
            "",
            "── Timing ──────────────────────────────",
            f"Wall time      : {metrics.elapsed_wall_s:.4f}s",
            f"CPU user time  : {metrics.cpu_time_user_s:.4f}s",
            f"CPU sys time   : {metrics.cpu_time_sys_s:.4f}s",
            "",
            "── Memory ──────────────────────────────",
            f"RSS before     : {metrics.rss_before_mb:.1f} MB",
            f"RSS after      : {metrics.rss_after_mb:.1f} MB",
            f"RSS delta      : {metrics.rss_delta_mb:+.1f} MB",
            "",
            "── Throughput ──────────────────────────",
            f"Input size     : {metrics.input_bytes / 1_048_576:.3f} MB",
            f"Output size    : {metrics.output_bytes / 1_048_576:.3f} MB",
            f"Throughput     : {metrics.throughput_mbps:.3f} MB/s",
        ]
        return "\n".join(lines)
