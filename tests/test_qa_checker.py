#!/usr/bin/env python3
"""
Unit tests for tools/audio/qa_checker.py

Tests the QA (Quality Assurance) checker functions for audio signal validation.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.audio.qa_checker import (
    compute_qa_metrics,
    determine_qa_status,
    validate_qa_strict,
)


class TestComputeQAMetrics:
    """Tests for compute_qa_metrics function."""

    def test_normal_signal(self):
        """Test QA metrics for a normal audio signal."""
        # Create a normal signal at -20 dBFS
        signal = np.random.randn(44100).astype(np.float32) * 0.1
        qa = compute_qa_metrics(signal)

        assert qa["clipping"] is False
        assert qa["peak_dbfs"] < 0  # Below 0 dBFS
        assert qa["rms_dbfs"] < 0  # Below 0 dBFS
        assert qa["silence_ratio"] < 0.5  # Not mostly silent

    def test_clipping_detection(self):
        """Test detection of clipping signals."""
        # Create a signal that clips
        signal = np.random.randn(44100).astype(np.float32)
        signal[100:200] = 1.0  # Peak at digital maximum

        qa = compute_qa_metrics(signal, clip_peak_threshold=0.999)

        assert qa["clipping"] is True
        assert qa["peak_dbfs"] >= -0.01  # Very close to 0 dBFS

    def test_silence_detection(self):
        """Test detection of mostly silent signals."""
        # Create a mostly silent signal
        signal = np.zeros(44100, dtype=np.float32)
        signal[100:200] = 0.001  # Small non-zero section

        qa = compute_qa_metrics(signal, silence_ratio_threshold=0.9)

        assert qa["silence_ratio"] > 0.95  # Mostly silent
        assert qa["rms_dbfs"] < -60  # Very quiet

    def test_low_level_signal(self):
        """Test detection of low-level signals."""
        # Create a very quiet signal
        signal = np.random.randn(44100).astype(np.float32) * 0.001

        qa = compute_qa_metrics(signal, low_level_dbfs_threshold=-40.0)

        assert qa["rms_dbfs"] < -40.0  # Below threshold
        assert qa["clipping"] is False

    def test_empty_signal(self):
        """Test handling of empty/None signals."""
        qa = compute_qa_metrics(None)

        assert qa["peak_dbfs"] == -float("inf")
        assert qa["rms_dbfs"] == -float("inf")
        assert qa["clipping"] is False
        assert qa["silence_ratio"] == 1.0

    def test_custom_thresholds(self):
        """Test that custom thresholds are stored in results."""
        signal = np.random.randn(44100).astype(np.float32) * 0.5
        qa = compute_qa_metrics(
            signal,
            clip_peak_threshold=0.95,
            silence_ratio_threshold=0.8,
            low_level_dbfs_threshold=-35.0,
        )

        assert qa["clip_peak_threshold"] == 0.95
        assert qa["silence_ratio_threshold"] == 0.8
        assert qa["low_level_dbfs_threshold"] == -35.0


class TestDetermineQAStatus:
    """Tests for determine_qa_status function."""

    def test_ok_status(self):
        """Test determination of OK status for good signals."""
        qa_metrics = {
            "clipping": False,
            "silence_ratio": 0.1,
            "rms_dbfs": -20.0,
            "peak_dbfs": -1.0,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        status, gate = determine_qa_status(qa_metrics)

        assert status == "ok"
        assert gate == "pass"

    def test_warn_clipping_status(self):
        """Test detection of clipping warning."""
        qa_metrics = {
            "clipping": True,
            "silence_ratio": 0.1,
            "rms_dbfs": -20.0,
            "peak_dbfs": -0.1,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        status, gate = determine_qa_status(qa_metrics)

        assert status == "warn_clipping"
        assert gate == "warn_clipping"

    def test_warn_silence_status(self):
        """Test detection of silence warning."""
        qa_metrics = {
            "clipping": False,
            "silence_ratio": 0.95,
            "rms_dbfs": -60.0,
            "peak_dbfs": -50.0,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        status, gate = determine_qa_status(qa_metrics)

        assert status == "warn_silence"
        assert gate == "warn_silence"

    def test_warn_low_level_status(self):
        """Test detection of low-level warning."""
        qa_metrics = {
            "clipping": False,
            "silence_ratio": 0.1,
            "rms_dbfs": -50.0,
            "peak_dbfs": -40.0,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        status, gate = determine_qa_status(qa_metrics)

        assert status == "warn_low_level"
        assert gate == "warn_low_level"

    def test_fail_on_clipping_threshold(self):
        """Test that fail_on_clipping_dbfs raises error."""
        qa_metrics = {
            "clipping": True,
            "peak_dbfs": -0.5,
            "silence_ratio": 0.1,
            "rms_dbfs": -20.0,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        with pytest.raises(RuntimeError, match="clipping error"):
            determine_qa_status(qa_metrics, fail_on_clipping_dbfs=-1.0)

    def test_priority_order(self):
        """Test that clipping takes priority over other warnings."""
        qa_metrics = {
            "clipping": True,
            "silence_ratio": 0.95,  # Would also trigger silence warning
            "rms_dbfs": -50.0,  # Would also trigger low-level warning
            "peak_dbfs": -0.1,
            "silence_ratio_threshold": 0.9,
            "low_level_dbfs_threshold": -40.0,
        }

        status, gate = determine_qa_status(qa_metrics)

        # Clipping takes priority
        assert status == "warn_clipping"
        assert gate == "warn_clipping"


class TestValidateQAStrict:
    """Tests for validate_qa_strict function."""

    def test_strict_ok_passes(self):
        """Test that OK status passes strict validation."""
        qa_metrics = {
            "peak_dbfs": -1.0,
            "rms_dbfs": -20.0,
            "silence_ratio": 0.1,
        }

        # Should not raise
        validate_qa_strict(qa_metrics, "ok")

    def test_strict_warn_fails(self):
        """Test that warnings fail strict validation."""
        qa_metrics = {
            "peak_dbfs": -0.1,
            "rms_dbfs": -20.0,
            "silence_ratio": 0.1,
        }

        with pytest.raises(RuntimeError, match="strict QA failed"):
            validate_qa_strict(qa_metrics, "warn_clipping")

    def test_strict_error_message(self):
        """Test that strict error message contains metrics."""
        qa_metrics = {
            "peak_dbfs": -0.1,
            "rms_dbfs": -20.0,
            "silence_ratio": 0.1,
        }

        with pytest.raises(RuntimeError) as exc_info:
            validate_qa_strict(qa_metrics, "warn_clipping")

        error_msg = str(exc_info.value)
        assert "peak_dbfs=-0.10" in error_msg
        assert "rms_dbfs=-20.00" in error_msg
        assert "silence_ratio=0.100" in error_msg


class TestEndToEndWorkflow:
    """Integration tests for the complete QA workflow."""

    def test_full_qa_workflow_ok(self):
        """Test complete workflow for a good signal."""
        # Create a deterministic signal (440 Hz sine wave at safe amplitude)
        # This ensures consistent test results without random clipping
        sr = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
        signal = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        # Compute metrics
        qa = compute_qa_metrics(signal)

        # Determine status
        status, gate = determine_qa_status(qa)

        # Should pass all checks
        assert status == "ok"
        assert gate == "pass"

        # Should pass strict validation
        validate_qa_strict(qa, status)  # Should not raise

    def test_full_qa_workflow_clipping(self):
        """Test complete workflow for a clipping signal."""
        # Create a clipping signal
        signal = np.random.randn(44100).astype(np.float32)
        signal = np.clip(signal, -1.0, 1.0)  # Ensure clipping

        # Compute metrics
        qa = compute_qa_metrics(signal)

        # Determine status
        status, gate = determine_qa_status(qa)

        # Should detect clipping
        assert status == "warn_clipping"
        assert gate == "warn_clipping"

        # Should fail strict validation
        with pytest.raises(RuntimeError, match="strict QA failed"):
            validate_qa_strict(qa, status)
