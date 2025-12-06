"""Compatibility wrapper for audio loader adapter."""
from ma_audio_engine.adapters_src import audio_loader_adapter as _loader

_MAX_FFMPEG_DURATION_SEC = _loader._MAX_FFMPEG_DURATION_SEC
load_audio_mono = _loader.load_audio_mono
sec_subprocess = _loader.sec_subprocess

__all__ = [
    "_MAX_FFMPEG_DURATION_SEC",
    "load_audio_mono",
    "sec_subprocess",
]
