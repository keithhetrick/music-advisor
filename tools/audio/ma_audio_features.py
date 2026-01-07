#!/usr/bin/env python3
"""
Pipeline feature extractor for MusicAdvisor HCI.

IMPORTANT:
- THIS is the canonical extractor used by:
    - Automator / shell workflows
    - tools/ma_simple_hci_from_features.py
    - HCI calibration tools
- It produces a flat top-level JSON:
    {
      "source_audio": "...",
      "sample_rate": ...,
      "duration_sec": ...,
      "tempo_bpm": ...,
      "key": "...",
      "mode": "major" | "minor" | "unknown",
      "loudness_LUFS": ...,
      "energy": 0.0..1.0,
      "danceability": 0.0..1.0,
      "valence": 0.0..1.0
    }

CLI:
    python tools/ma_audio_features.py --audio FILE --out FILE

Schema is stable: do NOT change keys or their meaning without
updating all HCI/axis/calibration consumers.

Debug/validation:
- Logs respect LOG_JSON/LOG_REDACT/LOG_SANDBOX via adapters.
- Validate outputs with `tools/validate_io.py --file <features.json>`.
- Sidecar details and confidence handling: see `docs/sidecar_tempo_key.md`; defaults from `adapters/confidence_adapter.py`.
"""

import argparse
import hashlib
import json
import math
import os
import shlex
import shutil
import sys
import tempfile
import time
import warnings
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from tools.audio.qa_checker import compute_qa_metrics, determine_qa_status, validate_qa_strict
from tools.audio.audio_loader import load_audio, probe_audio_duration

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from ma_audio_engine.adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_repo_root

ensure_repo_root()
REPO_ROOT = get_repo_root()

SIDECAR_CACHE_SCHEMA_V = 1

from ma_audio_engine.adapters import (
    TEMPO_CONF_DEFAULTS,
    build_config_components,
    confidence_label,
    get_backend_settings,
    get_default_sidecar_cmd,
    get_hash_params,
    hash_file,
    is_backend_enabled,
    load_json_guarded,
    load_audio_mono,
    load_runtime_settings,
    normalize_tempo_confidence,
    require_file,
    utc_now_iso,
)
from ma_audio_engine.adapters.cli_adapter import (
    add_log_format_arg,
    add_log_sandbox_arg,
    add_preflight_arg,
    apply_log_format_env,
    apply_log_sandbox_env,
    run_preflight_if_requested,
)
from tools.schema_utils import lint_features_payload, lint_json_file
from ma_audio_engine.adapters.service_registry import (
    get_cache,
    get_exporter,
    get_logger,
    get_structured_logger,
    get_logging_sandbox_defaults,
    get_qa_policy,
    scrub_payload_for_sandbox,
)
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from tools.sidecar_adapter import DEFAULT_SIDECAR_CMD as HITCH_DEFAULT_SIDECAR_CMD, run_sidecar, atomic_write_json
from security import files as sec_files
from security.config import CONFIG as SEC_CONFIG
from security import subprocess as sec_subprocess

# Cache dirs for librosa/numba to avoid failures when the Automator lacks a writable
# default cache location. Set early so imports honor them.
_TMP_CACHE_ROOT = Path(tempfile.gettempdir()) / "ma_audio_features_cache"
_TMP_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("LIBROSA_CACHE_DIR", str(_TMP_CACHE_ROOT / "librosa_cache"))
os.environ.setdefault("NUMBA_CACHE_DIR", str(_TMP_CACHE_ROOT / "numba_cache"))

# --- SciPy shim for librosa (hann removed in newer SciPy versions) ---
try:
    import scipy.signal as sps
    if not hasattr(sps, "hann"):
        from scipy.signal import windows as spw  # type: ignore

        def _hann(M, sym=True):
            return spw.hann(M, sym=sym)

        sps.hann = _hann  # type: ignore[attr-defined]
        warnings.filterwarnings("ignore", ".*hann.*", DeprecationWarning)
    warnings.filterwarnings("ignore", "pkg_resources is deprecated.*", UserWarning)
except Exception:
    # If SciPy isn't present or something else goes wrong, just continue.
    pass

# --- Backend normalization ---
def _sanitize_tempo_backend_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Force tempo backend fields into a safe, known set without changing schema keys."""
    cleaned = payload
    allowed_details = {"essentia", "madmom", "librosa", "auto", "external"}
    backend_raw = cleaned.get("tempo_backend")
    backend = "external" if isinstance(backend_raw, str) and backend_raw.strip() == "external" else "librosa"

    detail_raw = cleaned.get("tempo_backend_detail")
    if backend == "librosa":
        detail = "librosa"
    else:
        if isinstance(detail_raw, str) and detail_raw.strip() in allowed_details:
            detail = detail_raw.strip()
            if detail == "auto":
                detail = "external"
        else:
            detail = "external"

    meta = cleaned.get("tempo_backend_meta")
    meta_version = None
    if isinstance(meta, dict):
        if isinstance(meta.get("backend_version"), str):
            meta_version = meta["backend_version"]
    meta_backend_raw = meta.get("backend") if isinstance(meta, dict) else None
    if backend == "librosa":
        meta_backend = "librosa"
    else:
        if isinstance(meta_backend_raw, str) and meta_backend_raw.strip() in allowed_details:
            meta_backend = meta_backend_raw.strip()
            if meta_backend == "auto":
                meta_backend = "external"
        else:
            meta_backend = detail

    source = cleaned.get("tempo_backend_source")
    if backend == "external":
        source_val = source if isinstance(source, str) and source else "external"
    else:
        source_val = "librosa"

    cleaned["tempo_backend"] = backend
    cleaned["tempo_backend_detail"] = detail
    cleaned["tempo_backend_meta"] = {"backend": meta_backend, "backend_version": meta_version}
    cleaned["tempo_backend_source"] = source_val
    return cleaned


def _ensure_feature_pipeline_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Populate feature_pipeline_meta from existing top-level fields without altering schema."""
    meta_raw = payload.get("feature_pipeline_meta")
    meta: Dict[str, Any] = dict(meta_raw) if isinstance(meta_raw, dict) else {}

    def pick(key: str) -> Any:
        for src in (meta, payload):
            if isinstance(src, dict) and src.get(key) is not None:
                return src[key]
        return None

    meta.setdefault("source_hash", pick("source_hash") or "")
    meta.setdefault("config_fingerprint", pick("config_fingerprint") or "")
    meta.setdefault("pipeline_version", pick("pipeline_version") or "")
    meta.setdefault("generated_utc", pick("generated_utc") or pick("processed_utc"))
    meta.setdefault("sidecar_status", pick("sidecar_status"))
    meta.setdefault("sidecar_attempts", pick("sidecar_attempts"))
    meta.setdefault("sidecar_timeout_seconds", pick("sidecar_timeout_seconds"))
    meta.setdefault("tempo_backend", pick("tempo_backend"))
    meta.setdefault("tempo_backend_detail", pick("tempo_backend_detail"))
    if isinstance(pick("tempo_backend_meta"), dict):
        meta.setdefault("tempo_backend_meta", pick("tempo_backend_meta"))
    meta.setdefault("tempo_backend_source", pick("tempo_backend_source"))
    meta.setdefault("qa_gate", pick("qa_gate"))

    payload["feature_pipeline_meta"] = meta
    return payload

# --- Runtime dependency sanity (warn-only) ---
def _warn_if_dep_out_of_range() -> None:
    try:
        import importlib
        np_ver = importlib.import_module("numpy").__version__
        sp_ver = importlib.import_module("scipy").__version__
        lb_ver = importlib.import_module("librosa").__version__

        def _parse(v: str) -> tuple[int, int]:
            parts = v.split(".")[:2]
            return int(parts[0]), int(parts[1])

        def _in_range(ver: str, low: tuple[int, int], high: tuple[int, int]) -> bool:
            major_minor = _parse(ver)
            return low <= major_minor < high

        msgs = []
        if not _in_range(np_ver, (1, 23), (2, 0)):
            msgs.append(f"numpy {np_ver} (expected >=1.23,<2.0)")
        if not _in_range(sp_ver, (1, 9), (1, 12)):
            msgs.append(f"scipy {sp_ver} (expected >=1.9,<1.12)")
        if not _in_range(lb_ver, (0, 10), (0, 11)):
            msgs.append(f"librosa {lb_ver} (expected >=0.10,<0.11)")
        if msgs:
            warnings.warn("Dependency versions outside expected range: " + "; ".join(msgs))
    except Exception:
        # Soft-fail; do not block runtime.
        pass

_warn_if_dep_out_of_range()


def _git_sha() -> Optional[str]:
    try:
        completed = sec_subprocess.run_safe(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        return (completed.stdout or "").decode().strip() if isinstance(completed.stdout, (bytes, bytearray)) else str(completed.stdout).strip()
    except Exception:
        return None


def _dep_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for mod in ("numpy", "scipy", "librosa", "essentia", "madmom"):
        try:
            import importlib
            versions[mod] = importlib.import_module(mod).__version__  # type: ignore[attr-defined]
        except Exception:
            versions[mod] = "missing"
    return versions

try:
    import librosa
    import librosa.beat
    import librosa.feature
    import librosa.effects
    import librosa.onset
    import librosa.util
except ImportError:
    librosa = None

try:
    import pyloudnorm as pyln
except ImportError:
    pyln = None

try:
    import soundfile as sf
except Exception:
    sf = None

PIPELINE_VERSION = "ma_audio_features_v1.2"
TARGET_SR = 44100
TARGET_LUFS = -14.0  # internal normalization target; raw LUFS preserved
# QA thresholds (configurable via CLI)
CLIP_PEAK_THRESHOLD = 0.999
SILENCE_RATIO_THRESHOLD = 0.9
LOW_LEVEL_DBFS_THRESHOLD = -40.0
MAX_BEATS_LEN = 20000  # cap beats array to avoid bloat/DoS
MIN_TEMPO = 30.0
MAX_TEMPO = 260.0
MAX_TEMPO_CANDIDATES = 32
MAX_KEY_CANDIDATES = 24
ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".aif", ".aiff"}
MAX_AUDIO_BYTES = 1 << 30  # 1 GiB safety limit
MAX_JSON_BYTES = 5 << 20  # 5 MiB max for external JSON
MAX_AUDIO_DURATION_SEC = float(os.environ.get("MAX_AUDIO_DURATION_SEC", "900"))  # default 15 minutes
SIDECAR_CPU_LIMIT = os.environ.get("SIDECAR_CPU_LIMIT")
SIDECAR_MEM_LIMIT = os.environ.get("SIDECAR_MEM_LIMIT")  # bytes
ALLOW_CUSTOM_SIDECAR_CMD = os.environ.get("ALLOW_CUSTOM_SIDECAR_CMD", "0") == "1"
SIDECAR_TIMEOUT_SECONDS = int(os.environ.get("SIDECAR_TIMEOUT_SECONDS", "45")) if os.environ.get("SIDECAR_TIMEOUT_SECONDS", "45") else None
SIDECAR_RETRY_ATTEMPTS = int(os.environ.get("SIDECAR_RETRY_ATTEMPTS", "1"))
QA_STRICT_MODE = os.environ.get("QA_STRICT_MODE", "0") == "1"
TEMPO_CONF_STRICT_MIN = float(os.environ.get("TEMPO_CONF_STRICT_MIN", "0.25"))
SIDECAR_CACHE_DIR = os.environ.get("SIDECAR_CACHE_DIR")
SIDECAR_CACHE_MAX_BYTES = int(os.environ.get("SIDECAR_CACHE_MAX_BYTES", str(512 * (1 << 20))))  # 512 MiB default
TRACK_TIMEOUT_SECONDS = int(os.environ.get("TRACK_TIMEOUT_SECONDS", "0")) or None

# Apply QA policy overrides (env-driven; defaults retain current behavior)
QA_POLICY_NAME = os.environ.get("QA_POLICY", "default")
_qa_policy = get_qa_policy(QA_POLICY_NAME)
CLIP_PEAK_THRESHOLD = _qa_policy.clip_peak_threshold
SILENCE_RATIO_THRESHOLD = _qa_policy.silence_ratio_threshold
LOW_LEVEL_DBFS_THRESHOLD = _qa_policy.low_level_dbfs_threshold
CONFIG_COMPONENTS = build_config_components(
    target_sr=TARGET_SR,
    target_lufs=TARGET_LUFS,
    energy_hop=512,
    energy_frame=2048,
    tempo_backend="librosa.beat.beat_track",
    clip_peak_threshold=CLIP_PEAK_THRESHOLD,
    silence_ratio_threshold=SILENCE_RATIO_THRESHOLD,
    low_level_dbfs_threshold=LOW_LEVEL_DBFS_THRESHOLD,
)

NOTE_NAMES_SHARP = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]

DEFAULT_SIDECAR_CMD = get_default_sidecar_cmd()
LOG_REDACT = os.environ.get("LOG_REDACT", "0") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
LOG_JSON = os.getenv("LOG_JSON") == "1"
if LOG_JSON:
    _log = get_structured_logger("ma_audio_features", defaults={"tool": "ma_audio_features"})
else:
    _log = get_logger("ma_audio_features(tools)", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)
_SANDBOX_CFG = get_logging_sandbox_defaults()


def _coerce_float(val: Any, label: str, logger) -> Optional[float]:
    try:
        if val is None:
            return None
        out = float(val)
        if math.isnan(out) or math.isinf(out):
            logger(f"discarding {label}: nan/inf")
            return None
        return out
    except Exception:
        logger(f"discarding {label}: non-numeric")
        return None


def _validate_external_payload(
    payload: Any,
    *,
    logger,
    source: str,
    max_beats_len: int = MAX_BEATS_LEN,
) -> Optional[Dict[str, Any]]:
    """
    Harden external/sidecar payloads to avoid poisoning the pipeline.
    Drops untrusted fields and trims oversized arrays.
    """
    if not isinstance(payload, dict):
        logger(f"{source}: external payload not a mapping; ignoring")
        return None

    sanitized: Dict[str, Any] = {}
    tempo = _coerce_float(payload.get("tempo") or payload.get("tempo_bpm"), "tempo", logger)
    if tempo is not None and (tempo < MIN_TEMPO or tempo > MAX_TEMPO):
        logger(f"{source}: tempo out of bounds ({tempo:.2f}); dropping")
        tempo = None
    if tempo is not None:
        sanitized["tempo"] = tempo

    conf = _coerce_float(
        payload.get("tempo_confidence_score") or payload.get("tempo_confidence"), "tempo_confidence", logger
    )
    if conf is not None:
        sanitized["tempo_confidence_score"] = conf

    for alt_key in ("tempo_alt_half", "tempo_alt_double"):
        alt_val = _coerce_float(payload.get(alt_key), alt_key, logger)
        if alt_val is not None:
            sanitized[alt_key] = alt_val

    if isinstance(payload.get("tempo_alternates"), list):
        alts = [
            t for t in (_coerce_float(x, "tempo_alternate", logger) for x in payload.get("tempo_alternates"))
            if t is not None
        ]
        if alts:
            sanitized["tempo_alternates"] = alts[:MAX_TEMPO_CANDIDATES]

    if isinstance(payload.get("tempo_candidates"), list):
        candidates = []
        for cand in payload["tempo_candidates"][:MAX_TEMPO_CANDIDATES]:
            if not isinstance(cand, dict):
                continue
            t_val = _coerce_float(cand.get("tempo"), "tempo_candidate", logger)
            if t_val is None:
                continue
            c_val = _coerce_float(cand.get("confidence"), "tempo_candidate_conf", logger)
            entry = {"tempo": t_val}
            if c_val is not None:
                entry["confidence"] = c_val
            candidates.append(entry)
        if candidates:
            sanitized["tempo_candidates"] = candidates

    key = payload.get("key")
    if isinstance(key, str) and key.strip():
        sanitized["key"] = key.strip()
    mode = payload.get("mode")
    if isinstance(mode, str) and mode.strip():
        sanitized["mode"] = mode.strip().lower()
    key_strength = _coerce_float(payload.get("key_strength"), "key_strength", logger)
    if key_strength is not None:
        sanitized["key_strength"] = key_strength

    beats_sec = payload.get("beats_sec")
    if isinstance(beats_sec, list):
        trimmed = [
            b for b in (_coerce_float(x, "beat", logger) for x in beats_sec) if b is not None
        ]
        if len(trimmed) > max_beats_len:
            logger(f"{source}: beats_sec length {len(trimmed)} exceeds cap {max_beats_len}; trimming")
            trimmed = trimmed[:max_beats_len]
        sanitized["beats_sec"] = trimmed
        sanitized["beats_count"] = len(trimmed)
    elif isinstance(payload.get("beats_count"), int):
        sanitized["beats_count"] = payload["beats_count"]

    # Preserve backend metadata if present
    for meta_key in ("backend", "backend_version", "tempo_backend", "tempo_backend_detail", "tempo_backend_meta"):
        if meta_key in payload:
            sanitized[meta_key] = payload[meta_key]

    return sanitized if sanitized else None

def build_config_fingerprint() -> str:
    """
    Deterministic fingerprint of the pipeline configuration.
    Uses a sorted JSON string of the config components for stability.
    """
    return json.dumps(CONFIG_COMPONENTS, sort_keys=True)


def debug(msg: str) -> None:
    _log(msg)

def _pad_short_signal(y: Optional[np.ndarray], *, min_len: int = 2048, label: str = "short_signal") -> Optional[np.ndarray]:
    """
    Pad short signals to avoid librosa FFT warnings on tiny inputs.
    Returns the padded array (or original if already sufficient).
    """
    if y is None:
        return y
    if len(y) >= min_len:
        return y
    pad = min_len - len(y)
    debug(f"{label}_pad:{len(y)}->{min_len}")
    return np.pad(y, (0, pad), mode="constant")


def compute_file_hash(path: str, chunk_size: int = None) -> str:
    algo, default_chunk = get_hash_params()
    return hash_file(path, algorithm=algo, chunk_size=chunk_size or default_chunk)


def _warn_if_schema_mismatch(payload: Dict[str, Any]) -> None:
    required = {"source_audio", "tempo_bpm", "tempo_backend", "key", "mode", "pipeline_version"}
    missing = [k for k in required if k not in payload]
    if missing:
        debug(f"schema warning: missing required fields in features payload: {missing}")
    # sanity types (soft checks)
    if "tempo_bpm" in payload and not isinstance(payload["tempo_bpm"], (int, float)):
        debug("schema warning: tempo_bpm should be numeric")
    if "tempo_backend" in payload and not isinstance(payload["tempo_backend"], str):
        debug("schema warning: tempo_backend should be a string")


def estimate_lufs(y: np.ndarray, sr: int) -> Optional[float]:
    """
    Estimate integrated LUFS using pyloudnorm if available.
    Falls back to a simple RMS-based approximation if not.
    """
    if y is None or len(y) == 0:
        return None

    if pyln is not None:
        try:
            meter = pyln.Meter(sr)
            return float(meter.integrated_loudness(y))
        except Exception as e:
            debug(f"pyloudnorm failed, falling back to RMS: {e}")

    # Fallback: approximate LUFS from RMS
    rms = np.sqrt(np.mean(y * y) + 1e-12)
    lufs_approx = 20.0 * math.log10(rms + 1e-12) - 0.691
    return float(lufs_approx)


def normalize_audio(y: np.ndarray, sr: int, target_lufs: float = TARGET_LUFS) -> Tuple[np.ndarray, float, Optional[float]]:
    """
    Normalize audio to target LUFS (in-memory). Returns (y_norm, gain_db, norm_lufs).
    If LUFS cannot be computed, returns original signal and zero gain.
    """
    raw_lufs = estimate_lufs(y, sr)
    if raw_lufs is None:
        return y, 0.0, None

    gain_db = target_lufs - raw_lufs
    # Clamp extreme gains to avoid excessive boosts/cuts
    gain_db = float(np.clip(gain_db, -12.0, 12.0))
    gain = 10.0 ** (gain_db / 20.0)
    y_norm = y * gain
    norm_lufs = estimate_lufs(y_norm, sr)
    return y_norm, gain_db, norm_lufs


def estimate_energy(y, sr) -> Optional[float]:
    """
    Estimate perceptual energy on a 0..1 scale.

    - High (~0.7–0.9) for dense, consistently loud mixes.
    - Low (~0.1–0.3) for sparse/quiet ballads.
    - Relatively robust to uniform gain changes.
    """
    if librosa is None:
        return None
    if y is None or len(y) == 0:
        return None

    hop_length = 512
    frame_length = 2048
    try:
        rms = librosa.feature.rms(
            y=y,
            frame_length=frame_length,
            hop_length=hop_length,
            center=True
        )[0]
    except Exception:
        rms = np.array([np.sqrt(float(np.mean(y * y)) + 1e-12)])

    rms = np.maximum(rms, 1e-8)
    med = float(np.median(rms))
    if med <= 0.0:
        med = float(np.mean(rms))

    # Relative RMS vs median
    rms_rel = rms / (med + 1e-12)
    rms_rel = np.clip(rms_rel, 0.25, 5.0)

    x = float(np.mean(rms_rel))
    energy_core = 1.0 / (1.0 + np.exp(-(x - 1.5)))
    energy_core = 0.1 + 0.85 * float(np.clip(energy_core, 0.0, 1.0))

    # Add a brightness term from spectral centroid
    try:
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        cent_norm = float(
            np.clip(
                np.mean(cent) / (sr / 2.0 + 1e-9),
                0.0,
                1.0
            )
        )
    except Exception:
        cent_norm = 0.5

    energy = 0.8 * energy_core + 0.2 * cent_norm
    return float(np.clip(energy, 0.0, 1.0))


def estimate_danceability(y, sr, tempo) -> Optional[float]:
    """
    Estimate danceability on a 0..1 scale.

    Factors:
    - Tempo closeness to a comfortable dance window (~70–140 BPM, centered ~110).
    - Strength of beat pulses (onset energy on beats).
    - Regularity of beat energy across time.
    """
    if librosa is None:
        return None
    if y is None or len(y) == 0:
        return None

    # Tempo term: prefer typical dance tempo
    felt_tempo = float(tempo or 0.0)
    if felt_tempo <= 0:
        tempo_term = 0.5
    else:
        while felt_tempo < 60.0:
            felt_tempo *= 2.0
        while felt_tempo > 180.0:
            felt_tempo /= 2.0
        center = 110.0
        spread = 50.0
        delta = abs(felt_tempo - center)
        tempo_term = float(np.clip(1.0 - (delta / spread), 0.0, 1.0))

    # Beat strength & regularity
    try:
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        if np.max(oenv) <= 0:
            return float(tempo_term)

        tempo_est, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr)
        if beats is None or len(beats) < 4:
            beat_strength = float(
                np.clip(
                    np.mean(oenv) / (np.max(oenv) + 1e-9),
                    0.0,
                    1.0
                )
            )
            regularity = 0.5
        else:
            beat_env = oenv[beats].astype(float)
            if np.max(beat_env) > 0:
                beat_env = beat_env / np.max(beat_env)

            beat_strength = float(np.clip(np.mean(beat_env), 0.0, 1.0))

            if len(beat_env) > 1:
                mu = float(np.mean(beat_env))
                sigma = float(np.std(beat_env))
                cv = sigma / (mu + 1e-9)
                regularity = float(np.clip(1.0 - cv, 0.0, 1.0))
            else:
                regularity = 0.5
    except Exception:
        try:
            oenv = librosa.onset.onset_strength(y=y, sr=sr)
            if np.max(oenv) > 0:
                beat_strength = float(
                    np.clip(
                        np.mean(oenv) / (np.max(oenv) + 1e-9),
                        0.0,
                        1.0
                    )
                )
            else:
                beat_strength = 0.5
        except Exception:
            beat_strength = 0.5
        regularity = 0.5

    dance = (
        0.4 * beat_strength +
        0.3 * regularity +
        0.3 * tempo_term
    )
    return float(np.clip(dance, 0.0, 1.0))


def estimate_valence(mode, energy) -> Optional[float]:
    """
    Estimate valence on 0..1 scale.

    - Major keys bias upward, minor downward.
    - Higher energy nudges valence up.
    """
    if mode == "major":
        base = 0.7
    elif mode == "minor":
        base = 0.3
    else:
        base = 0.5

    e = 0.5 if energy is None else float(np.clip(energy, 0.0, 1.0))
    valence = 0.6 * base + 0.4 * e
    return float(np.clip(valence, 0.0, 1.0))


def robust_tempo(y: np.ndarray, sr: int) -> Optional[float]:
    """
    Tempo estimate using librosa.beat.beat_track with SciPy shim applied.
    """
    if librosa is None:
        return None
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, (list, np.ndarray)):
            tempo = float(tempo[0])
        return float(tempo)
    except Exception as e:
        debug(f"tempo estimation failed: {e}")
        return None


def _fold_tempo_to_window(bpm: float, low: float = 60.0, high: float = 180.0) -> float:
    folded = float(bpm)
    steps = 0
    while folded < low and steps < 6:
        folded *= 2.0
        steps += 1
    while folded > high and steps < 6:
        folded /= 2.0
        steps += 1
    return folded


def select_tempo_with_folding(base_tempo: Optional[float]) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    if base_tempo is None or base_tempo <= 0:
        return None, None, None, "no_tempo"

    candidates = [
        ("base", float(base_tempo)),
        ("half", float(base_tempo) / 2.0),
        ("double", float(base_tempo) * 2.0),
    ]
    best = None
    for label, bpm in candidates:
        if bpm <= 0:
            continue
        folded = _fold_tempo_to_window(bpm)
        # Prefer tempos that fold into the comfortable 60–180 window and near 110 BPM
        delta = abs(folded - 110.0)
        score = delta
        if best is None or score < best[0]:
            best = (score, label, bpm, folded)

    if best is None:
        return None, None, None, "no_valid_tempo"

    _, label, bpm, folded = best
    reason = f"{label}_selected_folded_to_{folded:.1f}_bpm"
    primary = folded
    alt_half = candidates[1][1]
    alt_double = candidates[2][1]
    return primary, alt_half, alt_double, reason


def estimate_tempo_with_folding(y: np.ndarray, sr: int) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    if librosa is None or y is None or len(y) == 0:
        return None, None, None, "librosa_unavailable_or_empty_audio"
    y = _pad_short_signal(y, min_len=1024, label="tempo_fold")
    base = robust_tempo(y, sr)
    if base is None:
        try:
            oenv = librosa.onset.onset_strength(y=y, sr=sr)
            temp = librosa.beat.tempo(onset_envelope=oenv, sr=sr, aggregate=np.median)
            if isinstance(temp, (list, np.ndarray)):
                base = float(temp[0])
            else:
                base = float(temp)
        except Exception as e:  # noqa: BLE001
            debug(f"fallback tempo estimation failed: {e}")
            base = None

    return select_tempo_with_folding(base)


def key_confidence_label(key_root: Optional[str]) -> str:
    return "med" if key_root else "low"


def compute_tempo_confidence(y: np.ndarray, sr: int, tempo_primary: Optional[float]) -> Tuple[float, str]:
    """
    Estimate tempo confidence using onset strength contrast, beat count, and tempogram peak near tempo.
    Returns (score 0..1, label low/med/high).
    """
    if tempo_primary is None or tempo_primary <= 0 or librosa is None or y is None or len(y) == 0:
        return 0.2, "low"
    y = _pad_short_signal(y, min_len=1024, label="tempo_conf")
    try:
        hop_length = 512
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        if oenv.size == 0:
            return 0.2, "low"
        contrast = float(np.max(oenv) / (np.mean(oenv) + 1e-9))
        contrast_norm = float(np.clip((contrast - 1.0) / 4.0, 0.0, 1.0))

        tempo_est, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop_length)
        beat_count = len(beats) if beats is not None else 0
        beat_norm = float(np.clip(beat_count / 32.0, 0.0, 1.0))

        tempogram = librosa.feature.tempogram(onset_envelope=oenv, sr=sr, hop_length=hop_length)
        tempos = librosa.tempo_frequencies(tempogram.shape[0], sr=sr, hop_length=hop_length)
        idx = int(np.argmin(np.abs(tempos - tempo_primary)))
        peak_near = float(tempogram[idx].max()) if tempogram.shape[1] > 0 else 0.0
        peak_global = float(tempogram.max()) if tempogram.size > 0 else 0.0
        peak_ratio = float(peak_near / (peak_global + 1e-9)) if peak_global > 0 else 0.0

        score = float(np.clip(0.4 * contrast_norm + 0.3 * beat_norm + 0.3 * peak_ratio, 0.0, 1.0))
        if score >= 0.66:
            label = "high"
        elif score >= 0.33:
            label = "med"
        else:
            label = "low"
        return score, label
    except Exception:
        return 0.2, "low"


def estimate_mode_and_key(y: np.ndarray, sr: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Crude key estimation: detect chroma, pick dominant pitch class,
    infer mode (major/minor) from relative brightness.
    """
    if librosa is None:
        return None, None
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        root_index = int(np.argmax(chroma_mean))
        key_root = NOTE_NAMES_SHARP[root_index]

        spread = float(np.std(chroma_mean))
        if spread > 0.05:
            mode = "major"
        else:
            mode = "minor"

        return key_root, mode
    except Exception as e:
        debug(f"mode/key estimation failed: {e}")
        return None, None


def normalize_external_confidence(
    raw_score: Optional[float],
    backend_hint: Optional[str],
    bounds: Optional[Tuple[float, float]] = None,
) -> Optional[float]:
    """
    Normalize an external tempo confidence score into 0..1.
    - Essentia's beat confidence (from RhythmExtractor2013) typically spans ~1.0..3.6 on our benchmark set;
      use a linear map with clipping based on that distribution.
    - Other backends: simple clamp to 0..1.
    """
    if raw_score is None:
        return None
    try:
        score = float(raw_score)
    except Exception:
        return None

    backend = (backend_hint or "").lower()
    defaults = TEMPO_CONF_DEFAULTS.get(backend, {})
    if bounds and len(bounds) == 2:
        lower, upper = bounds
    else:
        lower = defaults.get("lower")
        upper = defaults.get("upper")

    if lower is not None and upper is not None and upper != lower:
        norm = (score - float(lower)) / (float(upper) - float(lower))
        return float(np.clip(norm, 0.0, 1.0))

    return float(np.clip(score, 0.0, 1.0))


def normalize_key_confidence(raw_score: Optional[float]) -> Optional[float]:
    """Clamp key confidence/strength into 0..1."""
    if raw_score is None:
        return None
    try:
        return float(np.clip(float(raw_score), 0.0, 1.0))
    except Exception:
        return None


def analyze_pipeline(
    path: str,
    cache_dir: Optional[str] = ".ma_cache",
    cache_backend: str = "disk",
    use_cache: bool = True,
    force: bool = False,
    clip_peak_threshold: float = CLIP_PEAK_THRESHOLD,
    silence_ratio_threshold: float = SILENCE_RATIO_THRESHOLD,
    low_level_dbfs_threshold: float = LOW_LEVEL_DBFS_THRESHOLD,
    fail_on_clipping_dbfs: Optional[float] = None,
    external_tempo_json: Optional[str] = None,
    tempo_backend: str = "librosa",
    tempo_sidecar_cmd: Optional[str] = None,
    tempo_sidecar_json_out: Optional[str] = None,
    tempo_sidecar_keep: bool = False,
    tempo_sidecar_verbose: bool = False,
    tempo_sidecar_drop_beats: bool = False,
    tempo_sidecar_conf_lower: Optional[float] = None,
    tempo_sidecar_conf_upper: Optional[float] = None,
    require_sidecar: bool = False,
) -> Dict[str, Any]:
    """
    Analyze audio and return the flat pipeline feature structure.

    Notes:
    - Cache: controlled by cache_dir/cache_backend/use_cache/force; noop backend skips disk I/O.
    - Sidecar: tempo_backend="sidecar" wires external sidecar; require_sidecar enforces failure on fallback.
    - QA thresholds/confidence bounds are passed through for transparency in metadata.
    - Side effects: reads audio, may invoke external sidecar, may write cache depending on backend.
    """
    debug("USING_PIPELINE_EXTRACTOR_v1 (tools)")
    path_abs = os.path.abspath(path)
    # Basic path validation
    if not os.path.isfile(path_abs):
        raise RuntimeError(f"audio path is not a regular file: {path_abs}")
    if os.path.islink(path_abs):
        raise RuntimeError(f"audio path must not be a symlink: {path_abs}")
    ext = os.path.splitext(path_abs)[1].lower()
    sec_files.ensure_allowed_extension(path_abs, SEC_CONFIG.allowed_exts)
    sec_files.ensure_max_size(path_abs, SEC_CONFIG.max_file_bytes)
    duration_sec = probe_audio_duration(path_abs)
    probe_capable = bool(sf) or bool(shutil.which("ffprobe"))
    if probe_capable and duration_sec is None:
        raise RuntimeError("audio preflight failed or unsupported/invalid audio format")
    if duration_sec is not None and duration_sec > MAX_AUDIO_DURATION_SEC:
        raise RuntimeError(f"audio duration too long ({duration_sec:.2f}s > {MAX_AUDIO_DURATION_SEC:.2f}s limit)")
    source_mtime = os.path.getmtime(path_abs)
    source_hash = compute_file_hash(path_abs)
    git_sha = _git_sha()
    dep_versions = _dep_versions()

    config_components = CONFIG_COMPONENTS.copy()
    if tempo_backend == "sidecar":
        config_components["tempo_backend"] = "external_sidecar"
        config_components["tempo_sidecar_cmd"] = tempo_sidecar_cmd or DEFAULT_SIDECAR_CMD
        # Honor backend registry for sidecar selection (Essentia/Madmom/librosa/auto)
        allowed_backends = [b for b in ["essentia", "madmom", "librosa", "auto"] if is_backend_enabled(b)]
        if not allowed_backends:
            sidecar_status = "disabled"
            sidecar_warnings = ["sidecar_backend_disabled"]
            if require_sidecar:
                raise RuntimeError("sidecar backends disabled via registry; cannot satisfy --require-sidecar")
    tempo_backend_used = "librosa"
    key_backend_used = "librosa"
    external_data: Dict[str, Any] = {}
    external_source_path = external_tempo_json
    external_backend_hint: Optional[str] = None
    external_beats: Optional[Any] = None
    external_beats_count: Optional[int] = None
    external_key_strength_raw: Optional[float] = None
    external_backend_version: Optional[str] = None
    sidecar_status: str = "not_requested" if tempo_backend != "sidecar" else "requested"
    sidecar_warnings: list[str] = []
    sidecar_attempts_used: int = 0
    external_tempo_alternates: Optional[Any] = None
    external_key_candidates: Optional[Any] = None
    external_tempo_candidates: Optional[Any] = None
    start_wall_clock = time.time()

    if tempo_backend == "sidecar" and not external_source_path:
        cmd = tempo_sidecar_cmd
        if tempo_sidecar_verbose:
            cmd = (cmd or DEFAULT_SIDECAR_CMD) + " --verbose"
        if tempo_sidecar_drop_beats:
            cmd = (cmd or DEFAULT_SIDECAR_CMD) + " --drop-beats"
        if tempo_sidecar_conf_lower is not None and tempo_sidecar_conf_upper is not None:
            cmd = (cmd or DEFAULT_SIDECAR_CMD) + f" --tempo-conf-lower {tempo_sidecar_conf_lower} --tempo-conf-upper {tempo_sidecar_conf_upper}"
        # If registry disables specific sidecar backends, bias the default command to the first allowed backend.
        if (cmd is None or cmd.strip() == DEFAULT_SIDECAR_CMD) and tempo_backend == "sidecar":
            preferred_backend = None
            for cand in ["essentia", "madmom", "librosa"]:
                if is_backend_enabled(cand):
                    preferred_backend = cand
                    break
            if preferred_backend and not is_backend_enabled("auto"):
                cmd = (cmd or DEFAULT_SIDECAR_CMD) + f" --backend {preferred_backend}"
        if cmd is None and not allowed_backends:
            sidecar_status = "disabled"
            sidecar_warnings.append("sidecar_backend_disabled")
            if require_sidecar:
                raise RuntimeError("sidecar backends disabled via registry; cannot satisfy --require-sidecar")
            cmd = DEFAULT_SIDECAR_CMD
        sidecar_cache_dir: Optional[Path] = None
        sidecar_cache_path: Optional[Path] = None
        if use_cache:
            cache_dir = Path(SIDECAR_CACHE_DIR) if SIDECAR_CACHE_DIR else (REPO_ROOT / ".ma_cache" / "sidecar")
            cache_dir.mkdir(parents=True, exist_ok=True)
            sidecar_cache_dir = cache_dir
            cache_key = f"{source_hash}_{hashlib.sha1((cmd or DEFAULT_SIDECAR_CMD).encode()).hexdigest()}_v{SIDECAR_CACHE_SCHEMA_V}.json"
            sidecar_cache_path = cache_dir / cache_key
            if sidecar_cache_path.exists():
                cached_payload = load_json_guarded(sidecar_cache_path, max_bytes=MAX_JSON_BYTES, expect_mapping=True, logger=debug)
                cached_valid = _validate_external_payload(cached_payload, logger=debug, source="sidecar_cache")
                if cached_valid:
                    external_data = cached_valid
                    external_source_path = str(sidecar_cache_path)
                    sidecar_status = "cache_hit"
                    sidecar_attempts_used = 0
        if not external_data:
            max_attempts = max(1, SIDECAR_RETRY_ATTEMPTS + 1)
            attempt = 0
            sidecar_path = None
            while attempt < max_attempts:
                attempt += 1
                sidecar_data, sidecar_path, adapter_warnings = run_sidecar(
                    path_abs,
                    cmd,
                    tempo_sidecar_json_out,
                    keep_temp=tempo_sidecar_keep or tempo_sidecar_json_out is not None,
                    require_exec=require_sidecar,
                    allow_custom_cmd=ALLOW_CUSTOM_SIDECAR_CMD,
                    max_json_bytes=MAX_JSON_BYTES,
                    cpu_limit_seconds=int(SIDECAR_CPU_LIMIT) if SIDECAR_CPU_LIMIT else None,
                    mem_limit_bytes=int(SIDECAR_MEM_LIMIT) if SIDECAR_MEM_LIMIT else None,
                    timeout_seconds=SIDECAR_TIMEOUT_SECONDS,
                    debug=debug,
                )
                if adapter_warnings:
                    sidecar_warnings.extend(adapter_warnings)
                if sidecar_data:
                    external_data = _validate_external_payload(sidecar_data, logger=debug, source="sidecar")
                    if external_data:
                        external_source_path = sidecar_path
                        sidecar_status = "used"
                        sidecar_attempts_used = attempt
                        break
                    sidecar_status = "invalid"
                    sidecar_warnings.append("sidecar_payload_invalid")
                else:
                    sidecar_status = "failed"
                    if attempt < max_attempts:
                        sidecar_warnings.append("sidecar_retrying")
                        debug(f"tempo sidecar attempt {attempt} failed; retrying ({attempt}/{max_attempts})")
            if sidecar_status != "used":
                sidecar_attempts_used = attempt
            if sidecar_status != "used":
                debug("tempo sidecar requested but failed; falling back to librosa backend")
                sidecar_warnings.append("sidecar_failed_fallback_librosa")
        elif sidecar_cache_path and sidecar_cache_path.exists():
            sidecar_status = "cache_hit"
        if external_data and sidecar_status == "used" and sidecar_cache_path and not sidecar_cache_path.exists():
            try:
                # Only cache payloads that passed validation; write atomically.
                if "sidecar_data" in locals() and sidecar_data:
                    atomic_write_json(sidecar_cache_path, sidecar_data)
            except Exception:
                pass

    if not external_data and external_source_path:
        raw_external = load_json_guarded(
            external_source_path, max_bytes=MAX_JSON_BYTES, expect_mapping=True, logger=debug
        )
        external_data = _validate_external_payload(raw_external, logger=debug, source="sidecar_file")
        if external_data:
            tempo_backend_used = "external"
            key_backend_used = "external"
            config_components["tempo_backend"] = "external_sidecar"
            if tempo_backend == "sidecar":
                config_components["tempo_sidecar_cmd"] = tempo_sidecar_cmd or DEFAULT_SIDECAR_CMD
            sidecar_status = "used"
        else:
            sidecar_status = "invalid"
            sidecar_warnings.append("sidecar_json_invalid_or_missing")
            if tempo_backend == "sidecar" and tempo_sidecar_json_out:
                debug(f"expected sidecar json at {external_source_path} but could not parse")

    if external_data and tempo_backend_used == "librosa":
        tempo_backend_used = "external"
        key_backend_used = "external"
        config_components["tempo_backend"] = "external_sidecar"
        if tempo_backend == "sidecar":
            config_components["tempo_sidecar_cmd"] = tempo_sidecar_cmd or DEFAULT_SIDECAR_CMD
        sidecar_status = "used"
    if "sidecar_timeout" in sidecar_warnings and sidecar_status != "used":
        sidecar_status = "timeout"
    if require_sidecar and tempo_backend == "sidecar" and sidecar_status != "used":
        if sidecar_status == "timeout":
            raise RuntimeError(f"sidecar timed out (SIDECAR_TIMEOUT_SECONDS={SIDECAR_TIMEOUT_SECONDS}); cannot satisfy --require-sidecar")
        raise RuntimeError("require_sidecar enabled but sidecar was not used; failing run")

    if TRACK_TIMEOUT_SECONDS is not None:
        elapsed = time.time() - start_wall_clock
        if elapsed > TRACK_TIMEOUT_SECONDS:
            raise RuntimeError(f"track processing exceeded TRACK_TIMEOUT_SECONDS={TRACK_TIMEOUT_SECONDS} (elapsed={elapsed:.1f}s)")

    config_fp = json.dumps(config_components, sort_keys=True)

    cache = None
    if use_cache:
        cache = get_cache(cache_dir, backend=cache_backend)
    if cache and not force:
        cached = cache.load(source_hash=source_hash, config_fingerprint=config_fp, source_mtime=source_mtime)
        if cached:
            if not isinstance(cached, dict) or "tempo_backend" not in cached or "source_audio" not in cached:
                debug("cache entry missing required fields; ignoring")
            else:
                if "qa_status" not in cached and isinstance(cached.get("qa"), dict) and "status" in cached["qa"]:
                    cached["qa_status"] = cached["qa"].get("status")
                cached = _sanitize_tempo_backend_fields(cached)
                cached = _ensure_feature_pipeline_meta(cached)
                cached["cache_status"] = "hit"
                return cached

    y, sr = load_audio(path_abs)
    duration = float(len(y) / float(sr))

    # Measure raw LUFS (preserve true program loudness)
    loudness_raw = estimate_lufs(y, sr)

    # Normalize copy for feature stability
    y_proc, gain_db, loudness_norm = normalize_audio(y, sr, target_lufs=TARGET_LUFS)
    tempo_primary_internal, tempo_half_internal, tempo_double_internal, tempo_reason_internal = estimate_tempo_with_folding(y_proc, sr)
    tempo_conf_score_internal, tempo_conf_label_internal = compute_tempo_confidence(y_proc, sr, tempo_primary_internal)
    key_root_internal, mode_internal = estimate_mode_and_key(y_proc, sr)

    tempo_primary = tempo_primary_internal
    tempo_half = tempo_half_internal
    tempo_double = tempo_double_internal
    tempo_reason = tempo_reason_internal
    tempo_conf_score = tempo_conf_score_internal
    tempo_conf_score_raw: Optional[float] = tempo_conf_score_internal
    tempo_conf_label = tempo_conf_label_internal
    key_root = key_root_internal
    mode = mode_internal
    ext_key: Optional[str] = None
    ext_mode: Optional[str] = None
    # Optional half/double resolver for low-confidence internal librosa
    if tempo_backend_used == "librosa" and tempo_primary and tempo_conf_score is not None:
        low_conf = tempo_conf_score < 0.30
        in_ambiguous_band = tempo_primary < 80 or tempo_primary > 180
        if low_conf and in_ambiguous_band:
            current_score = tempo_conf_score
            best_tempo = tempo_primary
            best_score = current_score
            best_label = tempo_conf_label
            for alt in (tempo_primary / 2.0, tempo_primary * 2.0):
                if alt < MIN_TEMPO or alt > MAX_TEMPO:
                    continue
                alt_score, alt_label = compute_tempo_confidence(y_proc, sr, alt)
                if alt_score > best_score:
                    best_score = alt_score
                    best_label = alt_label
                    best_tempo = alt
            if best_tempo != tempo_primary:
                tempo_primary = best_tempo
                tempo_half = tempo_primary / 2.0
                tempo_double = tempo_primary * 2.0
                tempo_reason += "; auto_half_double_adjust"
                tempo_conf_score = best_score
                tempo_conf_score_raw = best_score
                tempo_conf_label = best_label

    if external_data:
        if not isinstance(external_data, dict):
            sidecar_warnings.append("sidecar_payload_not_mapping")
            external_data = {}
        ext_tempo = external_data.get("tempo") or external_data.get("tempo_bpm")
        ext_conf_score = external_data.get("tempo_confidence_score")
        ext_conf_label = external_data.get("tempo_confidence")
        ext_key = external_data.get("key")
        ext_mode = external_data.get("mode")
        external_backend_hint = external_data.get("backend")
        external_backend_version = external_data.get("backend_version")
        external_beats = external_data.get("beats_sec")
        if external_beats is not None and isinstance(external_beats, list) and len(external_beats) > MAX_BEATS_LEN:
            sidecar_warnings.append("sidecar_beats_truncated")
            external_beats = external_beats[:MAX_BEATS_LEN]
        external_beats_count = external_data.get("beats_count")
        external_key_strength_raw = external_data.get("key_strength") or external_data.get("key_strength_raw")
        external_tempo_alternates = external_data.get("tempo_alternates")
        external_key_candidates = external_data.get("key_candidates")
        external_tempo_candidates = external_data.get("tempo_candidates")
        external_conf_bounds = external_data.get("tempo_confidence_bounds")
        if not external_conf_bounds and external_backend_hint:
            backend_settings = get_backend_settings(external_backend_hint)
            bounds_from_registry = backend_settings.get("tempo_confidence_bounds")
            if isinstance(bounds_from_registry, list) and len(bounds_from_registry) == 2:
                try:
                    lower, upper = float(bounds_from_registry[0]), float(bounds_from_registry[1])
                    external_conf_bounds = (lower, upper)
                except Exception:
                    pass
        if external_backend_hint and not is_backend_enabled(external_backend_hint):
            sidecar_warnings.append("sidecar_backend_disabled")
            if require_sidecar:
                raise RuntimeError(f"sidecar backend '{external_backend_hint}' disabled via registry")
            external_data = {}
            external_backend_hint = None
            tempo_backend_used = "librosa"
            key_backend_used = "librosa"
            sidecar_status = "failed"
            tempo_reason = tempo_reason_internal
            tempo_conf_label = tempo_conf_label_internal
            tempo_conf_score = tempo_conf_score_internal
            tempo_conf_score_raw = tempo_conf_score_internal
            external_beats = None
            external_beats_count = None
            ext_tempo = None
            ext_key = None

        ext_conf_score_norm = normalize_tempo_confidence(ext_conf_score, bounds=external_conf_bounds, backend=external_backend_hint)
        if ext_conf_label is None:
            ext_conf_label = confidence_label(ext_conf_score_norm)
        if external_tempo_candidates and isinstance(external_tempo_candidates, list) and len(external_tempo_candidates) > MAX_TEMPO_CANDIDATES:
            sidecar_warnings.append("sidecar_tempo_candidates_truncated")
            external_tempo_candidates = external_tempo_candidates[:MAX_TEMPO_CANDIDATES]
        if ext_tempo is None:
            sidecar_warnings.append("sidecar_missing_tempo")
        if ext_key is None:
            sidecar_warnings.append("sidecar_missing_key")
        if external_beats is None:
            sidecar_warnings.append("sidecar_missing_beats")
        if external_backend_hint and not external_backend_version:
            sidecar_warnings.append("sidecar_backend_version_missing")
        # sanitize tempo candidates
        if external_tempo_candidates and isinstance(external_tempo_candidates, list):
            clean_tempo_cands = []
            for c in external_tempo_candidates:
                if not isinstance(c, dict):
                    continue
                tval = c.get("tempo")
                if tval is None or not math.isfinite(tval):
                    continue
                if tval < MIN_TEMPO or tval > MAX_TEMPO:
                    continue
                cand = {"tempo": float(tval)}
                conf = c.get("confidence")
                if conf is not None and math.isfinite(conf):
                    cand["confidence"] = float(conf)
                clean_tempo_cands.append(cand)
            if len(clean_tempo_cands) > MAX_TEMPO_CANDIDATES:
                sidecar_warnings.append("sidecar_tempo_candidates_truncated")
                clean_tempo_cands = clean_tempo_cands[:MAX_TEMPO_CANDIDATES]
            external_tempo_candidates = clean_tempo_cands
        # sanitize key candidates
        if external_key_candidates and isinstance(external_key_candidates, list):
            clean_key_cands = []
            for c in external_key_candidates:
                if not isinstance(c, dict):
                    continue
                k = c.get("key")
                m = c.get("mode")
                if not k or m not in ("major", "minor"):
                    continue
                strength = c.get("strength")
                if strength is not None and not math.isfinite(strength):
                    strength = None
                cand = {"key": k, "mode": m}
                if strength is not None:
                    cand["strength"] = float(strength)
                clean_key_cands.append(cand)
            if len(clean_key_cands) > MAX_KEY_CANDIDATES:
                sidecar_warnings.append("sidecar_key_candidates_truncated")
                clean_key_cands = clean_key_cands[:MAX_KEY_CANDIDATES]
            external_key_candidates = clean_key_cands
        if ext_tempo:
            tempo_primary = float(ext_tempo)
            if tempo_primary < MIN_TEMPO or tempo_primary > MAX_TEMPO:
                sidecar_warnings.append("sidecar_tempo_out_of_range")
                tempo_primary = max(MIN_TEMPO, min(MAX_TEMPO, tempo_primary))
            tempo_half = tempo_primary / 2.0
            tempo_double = tempo_primary * 2.0
            tempo_reason = f"external_backend:{os.path.basename(external_source_path) if external_source_path else 'sidecar'}"
        if ext_conf_score is not None and math.isfinite(ext_conf_score):
            tempo_conf_score_raw = float(ext_conf_score)
            tempo_conf_score = (
                ext_conf_score_norm
                if ext_conf_score_norm is not None
                else normalize_external_confidence(tempo_conf_score_raw, external_backend_hint, external_conf_bounds)
            )
            if tempo_sidecar_verbose and ext_conf_score_norm is not None:
                debug(
                    f"sidecar confidence normalized -> {tempo_conf_score:.3f} from raw={tempo_conf_score_raw} "
                    f"(backend={external_backend_hint or 'unknown'}, bounds={external_conf_bounds or 'auto'})"
                )
            if ext_conf_label:
                tempo_conf_label = str(ext_conf_label)
            else:
                tempo_conf_label = confidence_label(tempo_conf_score, backend=external_backend_hint, raw=tempo_conf_score_raw)
        else:
            tempo_conf_score, tempo_conf_label = compute_tempo_confidence(y_proc, sr, tempo_primary)
        # Half/double resolver for low-confidence external madmom/librosa
        if external_backend_hint in ("madmom", "librosa") and tempo_primary and tempo_conf_score is not None:
            conf_for_gate = tempo_conf_score
            low_conf = conf_for_gate < 0.30
            in_ambiguous_band = tempo_primary < 80 or tempo_primary > 180
            if low_conf and in_ambiguous_band:
                current_score = tempo_conf_score
                best_tempo = tempo_primary
                best_score = current_score
                best_label = tempo_conf_label
                for alt in (tempo_primary / 2.0, tempo_primary * 2.0):
                    if alt < MIN_TEMPO or alt > MAX_TEMPO:
                        continue
                    alt_score, alt_label = compute_tempo_confidence(y_proc, sr, alt)
                    if alt_score > best_score:
                        best_score = alt_score
                        best_label = alt_label
                        best_tempo = alt
                if best_tempo != tempo_primary:
                    tempo_primary = best_tempo
                    tempo_half = tempo_primary / 2.0
                    tempo_double = tempo_primary * 2.0
                    tempo_reason += "; auto_half_double_adjust"
                    tempo_conf_score = best_score
                    tempo_conf_label = best_label
    if ext_key:
        key_root = ext_key
        mode = ext_mode if ext_mode in ("major", "minor") else mode_internal
    energy = estimate_energy(y_proc, sr)
    dance = estimate_danceability(y_proc, sr, tempo_primary)
    valence = estimate_valence(mode, energy)
    if QA_STRICT_MODE and tempo_conf_score is not None and tempo_conf_score < TEMPO_CONF_STRICT_MIN:
        raise RuntimeError(f"strict QA failed (tempo_confidence {tempo_conf_score:.3f} < {TEMPO_CONF_STRICT_MIN})")

    # Optional source inspection before/after load
    source_info: Dict[str, Any] = {}
    if sf is not None:
        try:
            info = sf.info(path)
            source_info = {
                "orig_sample_rate": info.samplerate,
                "orig_channels": info.channels,
                "orig_format": info.format,
                "orig_subtype": info.subtype,
                "orig_duration_sec": (info.frames / info.samplerate) if info.samplerate else None,
            }
        except Exception as e:  # noqa: BLE001
            debug(f"soundfile inspect failed: {e}")

    # QA metrics on the loaded mono signal
    qa: Dict[str, Any] = {}
    qa_gate = "fail_missing_audio"
    if y is not None and len(y) > 0:
        qa = compute_qa_metrics(
            y,
            clip_peak_threshold=clip_peak_threshold,
            silence_ratio_threshold=silence_ratio_threshold,
            low_level_dbfs_threshold=low_level_dbfs_threshold,
        )
        qa_status, qa_gate = determine_qa_status(qa, fail_on_clipping_dbfs=fail_on_clipping_dbfs)
        qa["status"] = qa_status
        qa["gate"] = qa_gate
        if QA_STRICT_MODE:
            validate_qa_strict(qa, qa_status)

    now_ts = utc_now_iso(timespec="seconds")

    external_used = bool(external_data)
    allowed_details = {"essentia", "madmom", "librosa", "auto", "external"}
    tempo_backend_used = "external" if external_used else "librosa"
    backend_detail_hint = external_backend_hint if isinstance(external_backend_hint, str) else None
    if tempo_backend_used == "librosa":
        backend_detail = "librosa"
    else:
        if backend_detail_hint and backend_detail_hint in allowed_details:
            backend_detail = backend_detail_hint if backend_detail_hint != "auto" else "external"
        else:
            backend_detail = "external"

    key_confidence_score_norm = normalize_key_confidence(external_key_strength_raw) if (external_data and external_key_strength_raw is not None and math.isfinite(external_key_strength_raw)) else None

    data: Dict[str, Any] = {
        "source_audio": path_abs,
        "source_mtime": float(source_mtime),
        "sample_rate": int(sr),
        "duration_sec": float(duration),
        "tempo_bpm": float(tempo_primary) if tempo_primary is not None else 0.0,
        "tempo_primary": float(tempo_primary) if tempo_primary is not None else None,
        "tempo_alt_half": float(tempo_half) if tempo_half is not None else None,
        "tempo_alt_double": float(tempo_double) if tempo_double is not None else None,
        "tempo_choice_reason": tempo_reason,
        "tempo_confidence": tempo_conf_label,
        "tempo_confidence_score": tempo_conf_score,
        "tempo_confidence_score_raw": tempo_conf_score_raw,
        "tempo_backend": tempo_backend_used,
        "tempo_backend_source": external_source_path if external_data else "librosa",
        "tempo_backend_detail": backend_detail,
        "tempo_backend_meta": {
            "backend": backend_detail,
            "backend_version": external_backend_version if external_data else None,
        },
        "tempo_alternates": external_tempo_alternates,
        "tempo_beats_sec": None if external_data else None,
        "tempo_beats_count": external_beats_count if external_beats_count is not None else (len(external_beats) if isinstance(external_beats, list) else None),
        "tempo_candidates": external_tempo_candidates,
        "key_backend": key_backend_used,
        "key": key_root,
        "mode": mode if mode in ("major", "minor") else "unknown",
        "key_confidence": key_confidence_label(key_root),
        "key_confidence_score_raw": external_key_strength_raw,
        "key_confidence_score": key_confidence_score_norm,
        "key_candidates": external_key_candidates,
        "loudness_LUFS": float(loudness_raw) if loudness_raw is not None else 0.0,
        "loudness_LUFS_normalized": float(loudness_norm) if loudness_norm is not None else None,
        "loudness_normalization_gain_db": float(gain_db),
        "normalized_for_features": True,
        "energy": float(energy) if energy is not None else None,
        "danceability": float(dance) if dance is not None else None,
        "valence": float(valence) if valence is not None else None,
        "pipeline_version": PIPELINE_VERSION,
        "target_sample_rate": TARGET_SR,
        "config_fingerprint": config_fp,
        "generated_utc": now_ts,
        "processed_utc": now_ts,
        "source_hash": source_hash,
        "qa_gate": qa_gate,
        "sidecar_status": sidecar_status,
        "sidecar_attempts": sidecar_attempts_used,
        "sidecar_timeout_seconds": SIDECAR_TIMEOUT_SECONDS,
        "provenance": {
            "git_sha": git_sha,
            "deps": dep_versions,
            "track_id": source_hash[:12],
        },
    }
    if source_info:
        data["source_audio_info"] = source_info
    if qa:
        data["qa"] = qa
        data["qa_status"] = qa.get("status", "unknown")
    else:
        data["qa_status"] = "unknown"
    if cache:
        data["cache_status"] = "miss"
        cache.store(
            source_hash=source_hash,
            config_fingerprint=config_fp,
            payload=data,
            source_mtime=source_mtime,
        )
    else:
        data["cache_status"] = "disabled"
    if sidecar_warnings:
        data["sidecar_warnings"] = sidecar_warnings
        debug(f"sidecar warnings: {sidecar_warnings}")

    # Enforce sidecar cache cap if we wrote a new entry
    if use_cache and 'sidecar_cache_dir' in locals() and sidecar_cache_dir and sidecar_cache_dir.exists():
        try:
            entries = sorted(sidecar_cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            total = sum(p.stat().st_size for p in entries)
            while entries and total > SIDECAR_CACHE_MAX_BYTES:
                victim = entries.pop(0)
                size = victim.stat().st_size
                victim.unlink(missing_ok=True)
                total -= size
        except Exception:
            pass

    # Optional sandbox scrub (payload minimization/redaction)
    sandbox_cfg = dict(_SANDBOX_CFG)
    if os.environ.get("LOG_SANDBOX", "0") == "1":
        sandbox_cfg["enabled"] = True
    if sandbox_cfg.get("enabled"):
        data = scrub_payload_for_sandbox(data, sandbox_cfg)
        data.setdefault("sandbox_warnings", []).append("payload_sandbox_scrubbed")

    data = _sanitize_tempo_backend_fields(data)
    data = _ensure_feature_pipeline_meta(data)

    if external_data:
        # Keep a lean main payload: drop the full beat grid from the feature JSON, but leave count/meta.
        data["tempo_beats_sec"] = None
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline audio feature extractor for MusicAdvisor HCI.")
    add_log_format_arg(parser)
    add_log_sandbox_arg(parser)
    add_preflight_arg(parser)
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--out", required=True, help="Output JSON file (.features.json)")
    parser.add_argument("--cache-dir", default=".ma_cache", help="Cache directory for feature reuse (default: .ma_cache)")
    parser.add_argument(
        "--cache-backend",
        choices=["disk", "noop"],
        default=os.environ.get("CACHE_BACKEND", "disk"),
        help="Cache backend: disk (default) or noop to disable cache reads/writes without changing other flags.",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable on-disk feature cache")
    parser.add_argument("--force", action="store_true", help="Force recompute even if cache entry exists")
    parser.add_argument("--cache-gc", action="store_true", help="Run cache garbage collection and exit")
    parser.add_argument("--clip-peak-threshold", type=float, default=CLIP_PEAK_THRESHOLD, help="Clipping peak threshold (default: 0.999)")
    parser.add_argument("--silence-ratio-threshold", type=float, default=SILENCE_RATIO_THRESHOLD, help="Silence ratio threshold (default: 0.9)")
    parser.add_argument("--low-level-dbfs-threshold", type=float, default=LOW_LEVEL_DBFS_THRESHOLD, help="Low-level dBFS threshold (default: -40.0)")
    parser.add_argument(
        "--fail-on-clipping-dbfs",
        type=float,
        default=None,
        help="If set, hard-fail when peak_dbfs exceeds this value. Leaves minor clipping as warn-only by default.",
    )
    parser.add_argument("--external-tempo-json", help="Path to external tempo/key JSON to merge (fields: tempo, tempo_confidence_score/confidence, key, mode)")
    parser.add_argument(
        "--tempo-backend",
        choices=["librosa", "sidecar"],
        default="librosa",
        help="Choose tempo backend. 'sidecar' will run an external command and merge its JSON output; default: librosa.",
    )
    parser.add_argument(
        "--tempo-sidecar-cmd",
        help="Command template for tempo sidecar when --tempo-backend=sidecar. Use {audio} and {out} placeholders. Default runs tools/tempo_sidecar_runner.py.",
    )
    parser.add_argument(
        "--tempo-sidecar-json-out",
        help="Optional path to persist the sidecar JSON output when --tempo-backend=sidecar. If omitted, a temp file is used.",
    )
    parser.add_argument(
        "--tempo-sidecar-keep",
        action="store_true",
        help="When using --tempo-backend=sidecar, keep the generated sidecar JSON even if a temp path was used.",
    )
    parser.add_argument(
        "--tempo-sidecar-verbose",
        action="store_true",
        help="Append --verbose to the sidecar command to surface backend/logging details.",
    )
    parser.add_argument(
        "--tempo-sidecar-drop-beats",
        action="store_true",
        help="Ask the sidecar to omit beats_sec (keeps beats_count) to reduce payload size.",
    )
    parser.add_argument(
        "--tempo-sidecar-conf-lower",
        type=float,
        default=None,
        help="Override lower bound for sidecar tempo confidence normalization (Essentia).",
    )
    parser.add_argument(
        "--tempo-sidecar-conf-upper",
        type=float,
        default=None,
        help="Override upper bound for sidecar tempo confidence normalization (Essentia).",
    )
    parser.add_argument(
        "--qa-policy",
        choices=["default", "strict", "lenient"],
        default=None,
        help="Select QA policy preset (clipping/silence/low-level thresholds). Default honors QA_POLICY env or built-in defaults.",
    )
    parser.add_argument(
        "--require-sidecar",
        action="store_true",
        help="Fail if --tempo-backend=sidecar does not result in an external backend (no silent fallback to librosa).",
    )
    parser.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive strings from logs (also controllable via LOG_REDACT=1).",
    )
    parser.add_argument(
        "--log-redact-values",
        type=str,
        default=None,
        help="Comma-separated list of strings to redact from logs (also controllable via LOG_REDACT_VALUES).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if lint/schema warnings are found on outputs.",
    )
    args = parser.parse_args(argv)
    # Default to redacted logs unless explicitly disabled.
    os.environ.setdefault("LOG_REDACT", "1")
    apply_log_format_env(args)
    apply_log_sandbox_env(args)
    run_preflight_if_requested(args)

    global LOG_JSON, LOG_REDACT, LOG_REDACT_VALUES, _log
    LOG_JSON = os.getenv("LOG_JSON") == "1"
    LOG_REDACT = args.log_redact or os.environ.get("LOG_REDACT", "0") == "1"
    if args.log_redact_values:
        LOG_REDACT_VALUES = [v for v in args.log_redact_values.split(",") if v]
    else:
        LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
    if LOG_JSON:
        _log = get_structured_logger("ma_audio_features", defaults={"tool": "ma_audio_features"})
    else:
        _log = get_logger("ma_audio_features(tools)", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)

    settings = load_runtime_settings(args)

    if args.require_sidecar and os.getenv("ALLOW_REQUIRE_SIDECAR", "1") == "0":
        debug("require_sidecar suppressed by ALLOW_REQUIRE_SIDECAR=0 (sandbox mode)")
        args.require_sidecar = False

    if args.cache_gc:
        cache = get_cache(cache_dir=args.cache_dir, backend=args.cache_backend)
        stats = cache.gc()
        print(f"[ma_audio_features] cache gc -> removed temp={stats.get('temp_removed',0)} bad_entries={stats.get('entries_removed',0)}")
        return 0
    start_ts = time.perf_counter()
    if LOG_JSON:
        _log("start", {"event": "start", "audio": args.audio, "out": args.out, "tool": "ma_audio_features"})
        log_stage_start(_log, "analyze_pipeline", audio=args.audio, out=args.out, tempo_backend=args.tempo_backend, require_sidecar=args.require_sidecar)

    if args.qa_policy:
        policy = get_qa_policy(args.qa_policy)
        args.clip_peak_threshold = policy.clip_peak_threshold
        args.silence_ratio_threshold = policy.silence_ratio_threshold
        args.low_level_dbfs_threshold = policy.low_level_dbfs_threshold
    elif settings.qa_policy:
        policy = get_qa_policy(settings.qa_policy)
        args.clip_peak_threshold = policy.clip_peak_threshold
        args.silence_ratio_threshold = policy.silence_ratio_threshold
        args.low_level_dbfs_threshold = policy.low_level_dbfs_threshold
        args.qa_policy = settings.qa_policy

    # Fast sanity for required inputs
    if not require_file(args.audio, logger=debug):
        return 2
    if args.external_tempo_json and not require_file(args.external_tempo_json, logger=debug):
        return 2

    cache_dir = args.cache_dir or settings.cache_dir
    tempo_sidecar_conf_lower = args.tempo_sidecar_conf_lower
    tempo_sidecar_conf_upper = args.tempo_sidecar_conf_upper
    if tempo_sidecar_conf_lower is None:
        tempo_sidecar_conf_lower = settings.tempo_conf_lower
    if tempo_sidecar_conf_upper is None:
        tempo_sidecar_conf_upper = settings.tempo_conf_upper

    result = analyze_pipeline(
        path=args.audio,
        cache_dir=cache_dir,
        cache_backend=args.cache_backend,
        use_cache=not args.no_cache,
        force=args.force,
        clip_peak_threshold=args.clip_peak_threshold,
        silence_ratio_threshold=args.silence_ratio_threshold,
        low_level_dbfs_threshold=args.low_level_dbfs_threshold,
        fail_on_clipping_dbfs=args.fail_on_clipping_dbfs,
        external_tempo_json=args.external_tempo_json,
        tempo_backend=args.tempo_backend,
        tempo_sidecar_cmd=args.tempo_sidecar_cmd,
        tempo_sidecar_json_out=args.tempo_sidecar_json_out,
        tempo_sidecar_keep=args.tempo_sidecar_keep,
        tempo_sidecar_verbose=args.tempo_sidecar_verbose,
        tempo_sidecar_drop_beats=args.tempo_sidecar_drop_beats,
        tempo_sidecar_conf_lower=tempo_sidecar_conf_lower,
        tempo_sidecar_conf_upper=tempo_sidecar_conf_upper,
        require_sidecar=args.require_sidecar,
    )
    duration_ms = int((time.perf_counter() - start_ts) * 1000)

    _warn_if_schema_mismatch(result)
    lint_warns: list[str] = []
    lint_warns.extend(lint_features_payload(result))
    sidecar_warnings = result.get("sidecar_warnings") or []
    lint_warns.extend(sidecar_warnings)
    if args.tempo_sidecar_json_out and Path(args.tempo_sidecar_json_out).exists():
        sidecar_file_warnings, _ = lint_json_file(Path(args.tempo_sidecar_json_out), "sidecar")
        lint_warns.extend(sidecar_file_warnings)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    status = "ok"
    if lint_warns and args.strict:
        status = "error"
        _log(f"[ma_audio_features] lint warnings: {lint_warns}")

    if LOG_JSON:
        meta_log: Dict[str, Any] | None = None
        meta_src = result.get("feature_pipeline_meta")
        if isinstance(meta_src, dict):
            meta_log = dict(meta_src)
            if LOG_REDACT:
                for k in ("tempo_backend_source", "source_hash", "config_fingerprint"):
                    meta_log.pop(k, None)
        log_stage_end(
            _log,
            "analyze_pipeline",
            status=status,
            audio=args.audio,
            out=args.out,
            duration_ms=duration_ms,
            tempo_backend=result.get("tempo_backend"),
            tempo_confidence_score=result.get("tempo_confidence_score"),
            sidecar_status=result.get("sidecar_status"),
            cache_status=result.get("cache_status"),
            qa_status=result.get("qa_status"),
            qa_gate=result.get("qa_gate"),
            feature_pipeline_meta=meta_log,
            sidecar_lint_warnings=len(lint_warns),
            warnings=lint_warns,
        )
        _log(
            "end",
            {
                "event": "end",
                "audio": args.audio,
                "out": args.out,
                "status": status,
                "duration_ms": duration_ms,
                "cache_status": result.get("cache_status"),
                "qa_status": result.get("qa_status"),
                "qa_gate": result.get("qa_gate"),
                "sidecar_lint_warnings": len(lint_warns),
                "warnings": lint_warns,
            },
        )

    if status == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
