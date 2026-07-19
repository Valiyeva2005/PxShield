"""Tests for performance report module."""

import json
import pytest
from utils.perf_report import PerfRecorder, OperationMetrics


class TestPerfRecorder:
    def test_basic_roundtrip(self):
        recorder = PerfRecorder("encrypt", "test.png")
        recorder.start()
        import time; time.sleep(0.01)
        metrics = recorder.stop(input_bytes=1000, output_bytes=1100, algorithm="aes-256-gcm")

        assert metrics.operation == "encrypt"
        assert metrics.source_file == "test.png"
        assert metrics.elapsed_wall_s >= 0.01
        assert metrics.input_bytes == 1000
        assert metrics.output_bytes == 1100
        assert metrics.algorithm == "aes-256-gcm"
        assert metrics.throughput_mbps >= 0.0
        assert metrics.rss_before_mb > 0
        assert metrics.rss_after_mb > 0
        assert metrics.timestamp != ""

    def test_save_and_load_json(self, tmp_path):
        recorder = PerfRecorder("decrypt", "test.psh")
        recorder.start()
        metrics = recorder.stop(input_bytes=500)
        path = tmp_path / "perf.json"
        recorder.save(metrics, path)

        data = json.loads(path.read_text())
        assert data["operation"] == "decrypt"
        assert data["source_file"] == "test.psh"
        assert "elapsed_wall_s" in data

    def test_format_report_contains_expected_sections(self):
        recorder = PerfRecorder("encrypt", "image.png")
        recorder.start()
        metrics = recorder.stop(input_bytes=2_097_152, output_bytes=2_100_000, algorithm="hybrid")
        report = recorder.format_report(metrics)

        assert "Timing" in report
        assert "Memory" in report
        assert "Throughput" in report
        assert "hybrid" in report

    def test_ops_applied_stored(self):
        recorder = PerfRecorder("encrypt", "img.png")
        recorder.start()
        metrics = recorder.stop(ops_applied=["pixel_shuffle", "channel_rotation"])
        assert "pixel_shuffle" in metrics.ops_applied
        assert "channel_rotation" in metrics.ops_applied

    def test_throughput_zero_when_empty_input(self):
        recorder = PerfRecorder("encrypt", "x.png")
        recorder.start()
        metrics = recorder.stop(input_bytes=0)
        assert metrics.throughput_mbps == 0.0
