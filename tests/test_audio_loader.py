#!/usr/bin/env python3
"""
Unit tests for tools/audio/audio_loader.py

Tests audio loading utilities including format handling, duration probing,
and error cases.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from tools.audio.audio_loader import (
    load_audio,
    load_audio_mono,
    probe_audio_duration,
)


class TestLoadAudio:
    """Tests for load_audio function."""

    @patch("tools.audio.audio_loader.load_audio_mono")
    def test_load_audio_delegates_to_mono_loader(self, mock_loader):
        """Test that load_audio delegates to load_audio_mono."""
        # Setup mock
        expected_signal = np.random.randn(44100).astype(np.float32)
        expected_sr = 44100
        mock_loader.return_value = (expected_signal, expected_sr)

        # Call load_audio
        signal, sr = load_audio("test.wav", sr=44100)

        # Verify delegation
        mock_loader.assert_called_once_with("test.wav", sr=44100)
        assert signal is expected_signal
        assert sr == expected_sr

    @patch("tools.audio.audio_loader.load_audio_mono")
    def test_load_audio_with_custom_sample_rate(self, mock_loader):
        """Test load_audio with non-default sample rate."""
        mock_loader.return_value = (np.zeros(22050, dtype=np.float32), 22050)

        signal, sr = load_audio("test.wav", sr=22050)

        mock_loader.assert_called_once_with("test.wav", sr=22050)
        assert sr == 22050


class TestProbeAudioDuration:
    """Tests for probe_audio_duration function."""

    @patch("tools.audio.audio_loader.sf")
    def test_probe_with_soundfile(self, mock_sf):
        """Test duration probing using soundfile."""
        # Mock soundfile.info
        mock_info = Mock()
        mock_info.duration = 60.5
        mock_sf.info.return_value = mock_info

        duration = probe_audio_duration("test.wav")

        assert duration == 60.5
        mock_sf.info.assert_called_once_with("test.wav")

    @patch("tools.audio.audio_loader.sf", None)
    @patch("tools.audio.audio_loader.shutil.which")
    @patch("tools.audio.audio_loader.subprocess.run")
    def test_probe_with_ffprobe(self, mock_run, mock_which):
        """Test duration probing using ffprobe fallback."""
        # Mock ffprobe availability
        mock_which.return_value = "/usr/bin/ffprobe"

        # Mock ffprobe output
        mock_result = Mock()
        mock_result.stdout = b"120.456\n"
        mock_run.return_value = mock_result

        duration = probe_audio_duration("test.mp3")

        assert duration == 120.456
        mock_which.assert_called_once_with("ffprobe")
        mock_run.assert_called_once()

    @patch("tools.audio.audio_loader.sf")
    def test_probe_with_invalid_duration(self, mock_sf):
        """Test probe handles invalid/negative durations."""
        # Mock soundfile returning invalid duration
        mock_info = Mock()
        mock_info.duration = -1.0
        mock_sf.info.return_value = mock_info

        # Mock ffprobe not available
        with patch("tools.audio.audio_loader.shutil.which", return_value=None):
            duration = probe_audio_duration("test.wav")

        # Should return None for invalid duration
        assert duration is None

    @patch("tools.audio.audio_loader.sf")
    def test_probe_with_nan_duration(self, mock_sf):
        """Test probe handles NaN durations."""
        mock_info = Mock()
        mock_info.duration = float("nan")
        mock_sf.info.return_value = mock_info

        with patch("tools.audio.audio_loader.shutil.which", return_value=None):
            duration = probe_audio_duration("test.wav")

        assert duration is None

    @patch("tools.audio.audio_loader.sf")
    def test_probe_with_soundfile_error(self, mock_sf):
        """Test probe falls back to ffprobe when soundfile fails."""
        # Mock soundfile raising exception
        mock_sf.info.side_effect = Exception("Read error")

        # Mock successful ffprobe
        with patch("tools.audio.audio_loader.shutil.which", return_value="/usr/bin/ffprobe"):
            with patch("tools.audio.audio_loader.subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.stdout = b"45.0\n"
                mock_run.return_value = mock_result

                duration = probe_audio_duration("test.mp3")

        assert duration == 45.0

    @patch("tools.audio.audio_loader.sf", None)
    @patch("tools.audio.audio_loader.shutil.which")
    def test_probe_with_no_probe_methods(self, mock_which):
        """Test probe returns None when no probe methods available."""
        mock_which.return_value = None

        duration = probe_audio_duration("test.mp3")

        assert duration is None

    @patch("tools.audio.audio_loader.sf", None)
    @patch("tools.audio.audio_loader.shutil.which")
    @patch("tools.audio.audio_loader.subprocess.run")
    def test_probe_with_ffprobe_error(self, mock_run, mock_which):
        """Test probe returns None when ffprobe fails."""
        mock_which.return_value = "/usr/bin/ffprobe"
        mock_run.side_effect = Exception("ffprobe error")

        duration = probe_audio_duration("test.mp3")

        assert duration is None

    @patch("tools.audio.audio_loader.sf", None)
    @patch("tools.audio.audio_loader.shutil.which")
    @patch("tools.audio.audio_loader.subprocess.run")
    def test_probe_with_empty_ffprobe_output(self, mock_run, mock_which):
        """Test probe handles empty ffprobe output."""
        mock_which.return_value = "/usr/bin/ffprobe"
        mock_result = Mock()
        mock_result.stdout = b""
        mock_run.return_value = mock_result

        duration = probe_audio_duration("test.mp3")

        assert duration is None

    @patch("tools.audio.audio_loader.sf", None)
    @patch("tools.audio.audio_loader.shutil.which")
    @patch("tools.audio.audio_loader.subprocess.run")
    def test_probe_with_invalid_ffprobe_output(self, mock_run, mock_which):
        """Test probe handles non-numeric ffprobe output."""
        mock_which.return_value = "/usr/bin/ffprobe"
        mock_result = Mock()
        mock_result.stdout = b"invalid\n"
        mock_run.return_value = mock_result

        duration = probe_audio_duration("test.mp3")

        assert duration is None


class TestModuleExports:
    """Tests for module-level exports."""

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        from tools.audio import audio_loader

        assert hasattr(audio_loader, "__all__")
        assert "load_audio" in audio_loader.__all__
        assert "load_audio_mono" in audio_loader.__all__
        assert "probe_audio_duration" in audio_loader.__all__

    def test_load_audio_mono_is_imported(self):
        """Test that load_audio_mono is available from module."""
        from tools.audio.audio_loader import load_audio_mono

        # Should be callable (from adapters)
        assert callable(load_audio_mono)


class TestIntegration:
    """Integration tests using real/mock audio data."""

    @patch("tools.audio.audio_loader.load_audio_mono")
    def test_load_and_process_workflow(self, mock_loader):
        """Test typical workflow: probe then load."""
        # Mock duration probe
        with patch("tools.audio.audio_loader.probe_audio_duration", return_value=60.0):
            duration = probe_audio_duration("test.wav")
            assert duration == 60.0

            # Mock loading
            signal = np.random.randn(44100 * 60).astype(np.float32)
            mock_loader.return_value = (signal, 44100)

            loaded_signal, sr = load_audio("test.wav")
            assert len(loaded_signal) == len(signal)
            assert sr == 44100

    @patch("tools.audio.audio_loader.probe_audio_duration")
    @patch("tools.audio.audio_loader.load_audio_mono")
    def test_reject_oversized_file_workflow(self, mock_loader, mock_probe):
        """Test workflow that rejects oversized files."""
        # Mock probe returning very long duration
        mock_probe.return_value = 1000.0  # 1000 seconds

        duration = probe_audio_duration("huge.mp3")

        # Should reject before loading
        if duration and duration > 900:  # 15 minute limit
            # Don't attempt to load
            pass
        else:
            load_audio("huge.mp3")

        # Verify load was never called
        mock_loader.assert_not_called()
