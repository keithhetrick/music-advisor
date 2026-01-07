#!/usr/bin/env python3
"""
Unit tests for tools/audio/key_detector.py

Tests the musical key and mode detection functions.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.audio.key_detector import (
    NOTE_NAMES_SHARP,
    estimate_mode_and_key,
    key_confidence_label,
    normalize_key_confidence,
)


class TestNoteNamesSharp:
    """Tests for NOTE_NAMES_SHARP constant."""

    def test_note_names_length(self):
        """Test that there are 12 pitch classes."""
        assert len(NOTE_NAMES_SHARP) == 12

    def test_note_names_content(self):
        """Test that all expected notes are present."""
        expected = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        assert NOTE_NAMES_SHARP == expected

    def test_note_names_order(self):
        """Test chromatic ordering."""
        assert NOTE_NAMES_SHARP[0] == "C"
        assert NOTE_NAMES_SHARP[6] == "F#"
        assert NOTE_NAMES_SHARP[11] == "B"


class TestEstimateModeAndKey:
    """Tests for estimate_mode_and_key function."""

    def test_normal_signal(self):
        """Test key/mode estimation for a normal audio signal."""
        # Create a signal with some harmonic content
        sr = 44100
        duration = 5
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        key, mode = estimate_mode_and_key(signal, sr)

        # Should return valid key/mode or None for both
        if key is not None:
            assert key in NOTE_NAMES_SHARP
        if mode is not None:
            assert mode in ("major", "minor")

    def test_sine_wave(self):
        """Test key detection with a pure sine wave."""
        # Create a pure 440 Hz (A4) sine wave
        sr = 44100
        duration = 5
        t = np.linspace(0, duration, sr * duration, dtype=np.float32)
        signal = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        key, mode = estimate_mode_and_key(signal, sr)

        # Pure sine should detect some key (likely "A" but not guaranteed)
        assert key is None or key in NOTE_NAMES_SHARP
        assert mode is None or mode in ("major", "minor")

    def test_empty_signal(self):
        """Test handling of empty signal."""
        signal = np.array([], dtype=np.float32)

        key, mode = estimate_mode_and_key(signal, sr=44100)

        # Should handle gracefully (likely returns None, None or raises handled exception)
        assert key is None or key in NOTE_NAMES_SHARP
        assert mode is None or mode in ("major", "minor")

    def test_silent_signal(self):
        """Test key detection for a silent signal."""
        signal = np.zeros(44100 * 5, dtype=np.float32)

        key, mode = estimate_mode_and_key(signal, sr=44100)

        # Silent signal may not produce reliable key detection
        assert key is None or key in NOTE_NAMES_SHARP
        assert mode is None or mode in ("major", "minor")

    def test_very_short_signal(self):
        """Test key detection with a very short signal."""
        signal = np.random.randn(1024).astype(np.float32) * 0.3

        key, mode = estimate_mode_and_key(signal, sr=44100)

        # Short signal should still attempt detection
        assert key is None or key in NOTE_NAMES_SHARP
        assert mode is None or mode in ("major", "minor")

    def test_returns_tuple(self):
        """Test that function always returns a 2-tuple."""
        sr = 44100
        duration = 3
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        result = estimate_mode_and_key(signal, sr)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_consistent_results(self):
        """Test that repeated calls give same results for same signal."""
        sr = 44100
        duration = 3
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        key1, mode1 = estimate_mode_and_key(signal, sr)
        key2, mode2 = estimate_mode_and_key(signal, sr)

        # Should be deterministic
        assert key1 == key2
        assert mode1 == mode2


class TestKeyConfidenceLabel:
    """Tests for key_confidence_label function."""

    def test_detected_key(self):
        """Test confidence label when key is detected."""
        for key in NOTE_NAMES_SHARP:
            label = key_confidence_label(key)
            assert label == "med"

    def test_none_key(self):
        """Test confidence label when no key detected."""
        label = key_confidence_label(None)
        assert label == "low"

    def test_empty_string(self):
        """Test confidence label with empty string (treated as falsy)."""
        label = key_confidence_label("")
        # Empty string is falsy, so should return "low"
        assert label == "low"

    def test_all_valid_keys(self):
        """Test confidence label for all valid pitch classes."""
        for key in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]:
            label = key_confidence_label(key)
            assert label == "med"

    def test_return_type(self):
        """Test that function always returns a string."""
        assert isinstance(key_confidence_label("C"), str)
        assert isinstance(key_confidence_label(None), str)


class TestNormalizeKeyConfidence:
    """Tests for normalize_key_confidence function."""

    def test_in_range_value(self):
        """Test normalization of values already in 0.0-1.0 range."""
        assert normalize_key_confidence(0.0) == 0.0
        assert normalize_key_confidence(0.5) == 0.5
        assert normalize_key_confidence(1.0) == 1.0

    def test_above_range_value(self):
        """Test clamping of values above 1.0."""
        assert normalize_key_confidence(1.5) == 1.0
        assert normalize_key_confidence(2.0) == 1.0
        assert normalize_key_confidence(100.0) == 1.0

    def test_below_range_value(self):
        """Test clamping of values below 0.0."""
        assert normalize_key_confidence(-0.5) == 0.0
        assert normalize_key_confidence(-1.0) == 0.0
        assert normalize_key_confidence(-100.0) == 0.0

    def test_none_value(self):
        """Test handling of None input."""
        assert normalize_key_confidence(None) is None

    def test_edge_cases(self):
        """Test edge case values."""
        # Very close to boundaries
        assert 0.0 <= normalize_key_confidence(0.001) <= 1.0
        assert 0.0 <= normalize_key_confidence(0.999) <= 1.0

        # Exactly at boundaries
        assert normalize_key_confidence(0.0) == 0.0
        assert normalize_key_confidence(1.0) == 1.0

    def test_return_type(self):
        """Test that function returns float or None."""
        result = normalize_key_confidence(0.5)
        assert isinstance(result, float)

        result_none = normalize_key_confidence(None)
        assert result_none is None

    def test_various_valid_scores(self):
        """Test normalization with various valid confidence scores."""
        test_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
        for val in test_values:
            result = normalize_key_confidence(val)
            assert result == val


class TestEndToEndWorkflow:
    """Integration tests for the complete key detection workflow."""

    def test_full_key_detection_workflow(self):
        """Test complete workflow: detect key/mode and compute confidence."""
        # Create a signal
        sr = 44100
        duration = 5
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        # Detect key and mode
        key, mode = estimate_mode_and_key(signal, sr)

        # Get confidence label
        confidence = key_confidence_label(key)

        # Verify results
        if key is not None:
            assert key in NOTE_NAMES_SHARP
            assert confidence == "med"
        else:
            assert confidence == "low"

        if mode is not None:
            assert mode in ("major", "minor")

    def test_workflow_with_external_confidence(self):
        """Test workflow with external confidence normalization."""
        # Simulate external key detection
        sr = 44100
        duration = 5
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.3

        # Detect key
        key, mode = estimate_mode_and_key(signal, sr)

        # Simulate external confidence score
        external_confidence = 0.85

        # Normalize confidence
        normalized = normalize_key_confidence(external_confidence)

        # Get label
        confidence_label_result = key_confidence_label(key)

        # Verify all components work together
        assert normalized == 0.85
        assert confidence_label_result in ("low", "med")

    def test_workflow_consistency(self):
        """Test that workflow produces consistent results."""
        sr = 44100
        duration = 3
        signal = np.random.randn(sr * duration).astype(np.float32) * 0.5

        # Run workflow twice
        key1, mode1 = estimate_mode_and_key(signal, sr)
        conf1 = key_confidence_label(key1)

        key2, mode2 = estimate_mode_and_key(signal, sr)
        conf2 = key_confidence_label(key2)

        # Should get same results (deterministic)
        assert key1 == key2
        assert mode1 == mode2
        assert conf1 == conf2
