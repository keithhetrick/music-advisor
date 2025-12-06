"""
Whisper-based STT helpers and vocal separation utilities.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict

from security import subprocess as sec_subprocess
from security.config import CONFIG as SEC_CONFIG

def extract_vocals(audio_path: Path, log) -> Path:
    """
    Attempt to isolate vocals using an external separator (Demucs/UVR).
    Falls back to the original audio when unavailable or on failure.
    """
    separator_cmd = os.getenv("LYRIC_STT_SEPARATOR_CMD")
    if separator_cmd:
        cmd = separator_cmd.split()
        binary = cmd[0]
    else:
        binary = "demucs"
        cmd = [binary, "--two-stems=vocals"]
    if not shutil.which(binary):
        log(f"[WARN] Vocal separation tool not found ({binary}); using original audio.")
        return audio_path
    out_dir = audio_path.parent / f"{audio_path.stem}_stems"
    out_dir.mkdir(parents=True, exist_ok=True)
    full_cmd = cmd + ["-o", str(out_dir), str(audio_path)]
    try:
        sec_subprocess.run_safe(
            full_cmd,
            allow_roots=SEC_CONFIG.allowed_binary_roots,
            timeout=SEC_CONFIG.subprocess_timeout,
            check=True,
        )
    except Exception as exc:  # noqa: BLE001
        log(f"[WARN] Vocal separation failed ({binary}): {exc}; using original audio.")
        return audio_path
    vocals_candidates = list(out_dir.rglob("vocals*.wav"))
    if vocals_candidates:
        log(f"[INFO] Using separated vocals track: {vocals_candidates[0]}")
        return vocals_candidates[0]
    log("[WARN] Vocal separation produced no vocals track; using original audio.")
    return audio_path


def transcribe_audio(audio_path: Path, log) -> Dict[str, object]:
    """
    Transcribe audio using local Whisper if available.
    Returns a dict with `text` and `segments` keys.
    """
    try:
        import whisper  # type: ignore
    except Exception as exc:  # noqa: BLE001
        log(f"[WARN] Whisper not available ({exc}); returning empty transcript.")
        return {"text": "", "segments": []}
    model_name = os.getenv("LYRIC_STT_WHISPER_MODEL", "medium")
    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path))
        return {
            "text": result.get("text", "") or "",
            "segments": result.get("segments", []) or [],
        }
    except Exception as exc:  # noqa: BLE001
        log(f"[WARN] Whisper transcription failed: {exc}; returning empty transcript.")
        return {"text": "", "segments": []}


def transcribe_audio_alt(audio_path: Path, log) -> Dict[str, object]:
    """
    Alternate STT path (faster-whisper if available). Falls back to empty on failure.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # noqa: BLE001
        log(f"[WARN] Alternate STT (faster-whisper) not available ({exc}); skipping alt path.")
        return {"text": "", "segments": []}
    model_size = os.getenv("LYRIC_STT_ALT_MODEL", "medium")
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="float32")
        segments, _ = model.transcribe(str(audio_path))
        seg_list = []
        texts = []
        for seg in segments:
            seg_list.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
            texts.append(seg.text.strip())
        return {"text": " ".join(texts), "segments": seg_list}
    except Exception as exc:  # noqa: BLE001
        log(f"[WARN] Alternate STT transcription failed: {exc}; returning empty transcript.")
        return {"text": "", "segments": []}


def build_lyrics_from_segments(stt_result: Dict[str, object]) -> str:
    segments = stt_result.get("segments") or []
    lines = []
    if isinstance(segments, list):
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            text = (seg.get("text") or "").strip()
            if text:
                lines.append(text)
    if lines:
        return "\n".join(lines)
    return (stt_result.get("text") or "").strip()
