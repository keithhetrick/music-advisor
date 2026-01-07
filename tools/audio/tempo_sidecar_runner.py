#!/usr/bin/env python3
"""
Minimal tempo/key sidecar wrapper.

- Prefers Essentia or Madmom if installed; falls back to librosa-based estimators.
- Outputs JSON with tempo, optional confidence, key, mode, and optional beat grid.

Example:
    python tools/tempo_sidecar_runner.py --audio song.wav --out /tmp/tempo.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ma_audio_engine.adapters.bootstrap import ensure_repo_root
ensure_repo_root()

from tools.audio import ma_audio_features as pipeline  # noqa: E402
from ma_audio_engine.adapters import (  # noqa: E402
    add_log_sandbox_arg,
    add_log_format_arg,
    add_preflight_arg,
    apply_log_sandbox_env,
    apply_log_format_env,
    run_preflight_if_requested,
    require_file,
)
from ma_audio_engine.adapters import load_log_settings, load_runtime_settings
from ma_audio_engine.adapters.logging_adapter import log_stage_start, log_stage_end
from ma_audio_engine.adapters import di
from shared.ma_utils.schema_utils import lint_json_file
from shared.ma_utils.logger_factory import get_configured_logger

# Logging setup (allows LOG_SANDBOX via CLI/env)
_log = get_configured_logger("tempo_sidecar")

# Madmom uses collections.Mutable* and np.float on older releases; add small shims for 3.11+/NumPy>=1.20
import collections  # noqa: E402
import collections.abc as collections_abc  # noqa: E402

warnings.filterwarnings("ignore", "pkg_resources is deprecated.*", UserWarning)
warnings.filterwarnings("ignore", ".*np.bool.*", FutureWarning)
for name in ("MutableSequence", "MutableMapping", "MutableSet"):
    if not hasattr(collections, name) and hasattr(collections_abc, name):
        setattr(collections, name, getattr(collections_abc, name))

import numpy as np  # noqa: E402
# NumPy 1.24+ removes deprecated aliases; add light shims for older libs
if not hasattr(np, "float"):
    np.float = np.float64  # type: ignore[attr-defined]
if not hasattr(np, "int"):
    np.int = np.int64  # type: ignore[attr-defined]
if not hasattr(np, "complex"):
    np.complex = np.complex128  # type: ignore[attr-defined]
if not hasattr(np, "bool"):
    np.bool = bool  # type: ignore[attr-defined]

try:
    import essentia.standard as es  # type: ignore
except Exception:
    es = None

try:
    import madmom as mm  # type: ignore
except Exception:
    mm = None

try:
    from madmom.features.beats import DBNBeatTrackingProcessor, RNNBeatProcessor  # type: ignore
    from madmom.features.key import CNNKeyRecognitionProcessor, key_prediction_to_label  # type: ignore
    from madmom.features.tempo import TempoEstimationProcessor  # type: ignore
except Exception:
    RNNBeatProcessor = None
    DBNBeatTrackingProcessor = None
    TempoEstimationProcessor = None
    CNNKeyRecognitionProcessor = None
    key_prediction_to_label = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Essentia/Madmom tempo/key sidecar wrapper.")
    p.add_argument("--audio", required=True, help="Path to audio file.")
    p.add_argument("--out", required=True, help="Path to write JSON payload.")
    p.add_argument(
        "--backend",
        choices=["auto", "essentia", "madmom", "librosa"],
        default="auto",
        help="Backend preference order (default: auto detection).",
    )
    p.add_argument("--sample-rate", type=int, default=pipeline.TARGET_SR, help="Target sample rate for loading audio.")
    p.add_argument("--verbose", action="store_true", help="Print debug logs to stderr.")
    p.add_argument(
        "--drop-beats",
        action="store_true",
        help="If set, omit beats_sec from the sidecar payload (keep beats_count only) to reduce file size.",
    )
    p.add_argument(
        "--tempo-conf-lower",
        type=float,
        default=None,
        help="Override lower bound for tempo confidence normalization (Essentia). Default calibrated on benchmark_set_v1_1.",
    )
    p.add_argument(
        "--tempo-conf-upper",
        type=float,
        default=None,
        help="Override upper bound for tempo confidence normalization (Essentia). Default calibrated on benchmark_set_v1_1.",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if lint/schema warnings are found in the sidecar payload.",
    )
    p.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    p.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(p)
    add_log_format_arg(p)
    add_preflight_arg(p)
    return p.parse_args()


def log(msg: str, verbose: bool, logger) -> None:
    if verbose:
        logger(msg)


def parse_key_mode(label: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize key/mode outputs from Essentia/Madmom/librosa.
    Essentia KeyExtractor can return (key, scale, strength); handle tuples/lists gracefully.
    """
    if isinstance(label, (tuple, list)):
        if len(label) >= 2:
            key_raw, mode_raw = label[0], label[1]
        elif len(label) == 1:
            key_raw, mode_raw = label[0], None
        else:
            return None, None
        label = f"{key_raw} {mode_raw or ''}"
    label = str(label).strip()
    if not label:
        return None, None
    lower = label.lower()
    mode = "major" if "maj" in lower else "minor" if "min" in lower else "unknown"
    parts = label.replace("major", "").replace("minor", "").replace("maj", "").replace("min", "").split()
    key = parts[0].strip().upper().replace("#", "#") if parts else None
    return key, mode


def get_backend_version(mod: Any, pkg_name: str) -> Optional[str]:
    """
    Try to extract a backend version from module or package metadata.
    """
    if mod is not None:
        v = getattr(mod, "__version__", None)
        if v:
            return str(v)
    try:
        import importlib.metadata as im

        return im.version(pkg_name)
    except Exception:
        return None


def run_with_essentia(audio_path: str, sample_rate: int, verbose: bool, logger) -> Optional[Dict[str, Any]]:
    if es is None:
        return None
    try:
        loader = es.MonoLoader(filename=audio_path, sampleRate=sample_rate)
        audio = loader()
        rhythm = es.RhythmExtractor2013(method="multifeature")
        tempo, beats, beat_confidence, _, beat_positions = rhythm(audio)
        key_extractor = es.KeyExtractor()
        key_label = key_extractor(audio)
        key, mode = parse_key_mode(key_label)
        key_strength = None
        if isinstance(key_label, (tuple, list)) and len(key_label) >= 3:
            try:
                key_strength = float(key_label[2])
            except Exception:
                key_strength = None
        backend_version = get_backend_version(es, "essentia")
        tempo_alts = None
        tempo_candidates = None
        if tempo:
            tempo_alts = [float(tempo / 2.0), float(tempo * 2.0)]
            tempo_candidates = [
                {"tempo": float(tempo), "confidence": float(beat_confidence) if beat_confidence is not None else None},
                {"tempo": float(tempo / 2.0), "confidence": None},
                {"tempo": float(tempo * 2.0), "confidence": None},
            ]
        key_candidates = None
        if key:
            key_candidates = [{"key": key, "mode": mode, "strength": key_strength}]
        return {
            "backend": "essentia",
            "backend_version": backend_version,
            "tempo": float(tempo) if tempo else None,
            "tempo_confidence_score": float(beat_confidence) if beat_confidence is not None else None,
            "tempo_confidence": "high" if beat_confidence and beat_confidence >= 0.66 else "med" if beat_confidence and beat_confidence >= 0.33 else "low",
            "key": key,
            "mode": mode,
            "key_strength": key_strength,
            "tempo_alternates": tempo_alts,
            "tempo_candidates": tempo_candidates,
            "key_candidates": key_candidates,
            "beats_sec": [float(b) for b in beat_positions] if beat_positions is not None else None,
            "beats_count": len(beat_positions) if beat_positions is not None else 0,
        }
    except Exception as e:  # noqa: BLE001
        log(f"Essentia backend failed: {e}", verbose, logger)
        return None


def run_with_madmom(audio_path: str, verbose: bool, logger) -> Optional[Dict[str, Any]]:
    if RNNBeatProcessor is None or DBNBeatTrackingProcessor is None:
        return None
    try:
        act = RNNBeatProcessor()(audio_path)
        tempo_candidates = TempoEstimationProcessor(fps=100)(act) if TempoEstimationProcessor else []
        tempo = float(tempo_candidates[0][0]) if len(tempo_candidates) > 0 else None
        tempo_conf = float(tempo_candidates[0][1]) if len(tempo_candidates) > 0 and len(tempo_candidates[0]) > 1 else None
        beat_times = DBNBeatTrackingProcessor(fps=100)(act)
        key_label = None
        if CNNKeyRecognitionProcessor and key_prediction_to_label:
            key_preds = CNNKeyRecognitionProcessor()(audio_path)
            key_label = key_prediction_to_label(key_preds)
        key, mode = parse_key_mode(key_label) if key_label else (None, None)
        backend_version = get_backend_version(mm, "madmom")
        tempo_alts = None
        tempo_candidates = None
        if tempo:
            tempo_alts = [float(tempo / 2.0), float(tempo * 2.0)]
            tempo_candidates = [
                {"tempo": float(tempo), "confidence": tempo_conf},
                {"tempo": float(tempo / 2.0), "confidence": None},
                {"tempo": float(tempo * 2.0), "confidence": None},
            ]
        result = {
            "backend": "madmom",
            "backend_version": backend_version,
            "tempo": tempo,
            "tempo_confidence_score": tempo_conf,
            "tempo_confidence": "high" if tempo_conf and tempo_conf >= 0.66 else "med" if tempo_conf and tempo_conf >= 0.33 else "low",
            "key": key,
            "mode": mode,
            "key_strength": None,
            "tempo_alternates": tempo_alts,
            "tempo_candidates": tempo_candidates,
            "key_candidates": None,
            "beats_sec": [float(b) for b in beat_times] if beat_times is not None else None,
            "beats_count": len(beat_times) if beat_times is not None else 0,
        }
        # Apply a guarded half/double resolver using pipeline confidence if low-conf and ambiguous tempo
        if tempo is not None and tempo_conf is not None:
            conf = float(tempo_conf)
            in_ambig = tempo < 80.0 or tempo > 180.0
            if conf < 0.30 and in_ambig:
                try:
                    y, sr = pipeline.load_audio(audio_path, sr=pipeline.TARGET_SR)
                    best_tempo = tempo
                    best_score = conf
                    best_label = result["tempo_confidence"]
                    for alt in (tempo / 2.0, tempo * 2.0):
                        if alt < pipeline.MIN_TEMPO or alt > pipeline.MAX_TEMPO:
                            continue
                        alt_score, alt_label = pipeline.compute_tempo_confidence(y, sr, alt)
                        if alt_score > best_score:
                            best_score = alt_score
                            best_label = alt_label
                            best_tempo = alt
                    if best_tempo != tempo:
                        result["tempo"] = best_tempo
                        result["tempo_confidence_score"] = best_score
                        result["tempo_confidence"] = best_label
                        result["tempo_alternates"] = [best_tempo / 2.0, best_tempo * 2.0]
                        result["tempo_candidates"] = [
                            {"tempo": best_tempo, "confidence": best_score},
                            {"tempo": best_tempo / 2.0, "confidence": None},
                            {"tempo": best_tempo * 2.0, "confidence": None},
                        ]
                except Exception:
                    pass
        return result
    except Exception as e:  # noqa: BLE001
        log(f"Madmom backend failed: {e}", verbose, logger)
        return None


def run_with_librosa(audio_path: str, sample_rate: int, verbose: bool, logger) -> Optional[Dict[str, Any]]:
    try:
        y, sr = pipeline.load_audio(audio_path, sr=sample_rate)
        tempo_primary, tempo_half, tempo_double, _ = pipeline.estimate_tempo_with_folding(y, sr)
        tempo_conf_score, tempo_conf_label = pipeline.compute_tempo_confidence(y, sr, tempo_primary)
        key_root, mode = pipeline.estimate_mode_and_key(y, sr)
        tempo_val = float(tempo_primary) if tempo_primary is not None else None
        tempo_alts = None
        tempo_candidates = None
        if tempo_val:
            tempo_alts = [float(tempo_val / 2.0), float(tempo_val * 2.0)]
            tempo_candidates = [
                {"tempo": float(tempo_val), "confidence": tempo_conf_score},
                {"tempo": float(tempo_val / 2.0), "confidence": None},
                {"tempo": float(tempo_val * 2.0), "confidence": None},
            ]
            # Guarded half/double resolver for low-confidence ambiguous tempos
            if tempo_conf_score is not None:
                low_conf = tempo_conf_score < 0.30
                in_ambig = tempo_val < 80.0 or tempo_val > 180.0
                if low_conf and in_ambig:
                    best_tempo = tempo_val
                    best_score = tempo_conf_score
                    best_label = tempo_conf_label
                    for alt in (tempo_val / 2.0, tempo_val * 2.0):
                        if alt < pipeline.MIN_TEMPO or alt > pipeline.MAX_TEMPO:
                            continue
                        alt_score, alt_label = pipeline.compute_tempo_confidence(y, sr, alt)
                        if alt_score > best_score:
                            best_score = alt_score
                            best_label = alt_label
                            best_tempo = alt
                    if best_tempo != tempo_val:
                        tempo_val = best_tempo
                        tempo_alts = [float(best_tempo / 2.0), float(best_tempo * 2.0)]
                        tempo_candidates = [
                            {"tempo": float(best_tempo), "confidence": best_score},
                            {"tempo": float(best_tempo / 2.0), "confidence": None},
                            {"tempo": float(best_tempo * 2.0), "confidence": None},
                        ]
                        tempo_conf_score = best_score
                        tempo_conf_label = best_label
        beats = None
        if pipeline.librosa is not None:
            try:
                oenv = pipeline.librosa.onset.onset_strength(y=y, sr=sr)
                _, beat_frames = pipeline.librosa.beat.beat_track(onset_envelope=oenv, sr=sr)
                if beat_frames is not None:
                    beats = pipeline.librosa.frames_to_time(beat_frames, sr=sr).tolist()
            except Exception:
                beats = None
        backend_version = get_backend_version(pipeline.librosa, "librosa") if pipeline.librosa is not None else None
        return {
            "backend": "librosa",
            "backend_version": backend_version,
            "tempo": tempo_val,
            "tempo_confidence_score": tempo_conf_score,
            "tempo_confidence": tempo_conf_label,
            "key": key_root,
            "mode": mode,
            "key_strength": None,
            "tempo_alternates": tempo_alts,
            "tempo_candidates": tempo_candidates,
            "key_candidates": None,
            "tempo_alt_half": float(tempo_half) if tempo_half is not None else None,
            "tempo_alt_double": float(tempo_double) if tempo_double is not None else None,
            "beats_sec": [float(b) for b in beats] if beats is not None else None,
            "beats_count": len(beats) if beats is not None else 0,
        }
    except Exception as e:  # noqa: BLE001
        log(f"Librosa fallback failed: {e}", verbose, logger)
        return None


def pick_backend(preference: str) -> Tuple[str, Tuple[Any, ...]]:
    if preference == "essentia" and es is not None:
        return "essentia", ()
    if preference == "madmom" and RNNBeatProcessor is not None:
        return "madmom", ()
    if preference == "librosa":
        return "librosa", ()
    if preference == "auto":
        if es is not None:
            return "essentia", ()
        if RNNBeatProcessor is not None:
            return "madmom", ()
        return "librosa", ()
    return "librosa", ()


def main() -> int:
    args = parse_args()
    apply_log_sandbox_env(args)
    apply_log_format_env(args)
    run_preflight_if_requested(args)
    # Load runtime settings up front so env/config defaults are consistent across CLIs.
    _ = load_runtime_settings(args)
    # Rebuild logger after potential log-sandbox toggle and runtime redaction inputs
    _ = load_log_settings(args)
    logger = get_configured_logger("tempo_sidecar")
    if not require_file(args.audio, logger=lambda m: logger(m)):
        return 2

    start_ts = time.perf_counter()
    if os.getenv("LOG_JSON") == "1":
        logger("start", {"event": "start", "audio": args.audio, "out": args.out, "tool": "tempo_sidecar"})
        log_stage_start(logger, "tempo_probe", audio=args.audio, out=args.out, requested_backend=args.backend)

    backend, _ = pick_backend(args.backend)
    log(f"selected backend={backend}", args.verbose, logger)

    result: Optional[Dict[str, Any]] = None
    if backend == "essentia":
        result = run_with_essentia(args.audio, args.sample_rate, args.verbose, logger)
        if result is None and args.backend == "auto":
            backend = "madmom" if RNNBeatProcessor is not None else "librosa"
    if result is None and backend == "madmom":
        result = run_with_madmom(args.audio, args.verbose, logger)
        if result is None and args.backend == "auto":
            backend = "librosa"
    if result is None:
        result = run_with_librosa(args.audio, args.sample_rate, args.verbose, logger)

    if result is None:
        log("All tempo sidecar backends failed.", True, logger)
        if os.getenv("LOG_JSON") == "1":
            log_stage_end(logger, "tempo_probe", status="error", selected_backend=backend, reason="all_backends_failed")
        return 1

    # Normalize mode label
    if result.get("mode") not in ("major", "minor"):
        result["mode"] = "unknown"

    # Apply optional/default confidence bounds hint for normalization downstream
    if args.tempo_conf_lower is not None and args.tempo_conf_upper is not None:
        result["tempo_confidence_bounds"] = [float(args.tempo_conf_lower), float(args.tempo_conf_upper)]
    elif result.get("backend") == "essentia":
        # Default calibration
        result["tempo_confidence_bounds"] = [0.9, 3.6]

    # Optionally strip beat grid to keep payload small
    if args.drop_beats and "beats_sec" in result:
        result["beats_sec"] = None

    duration_ms = int((time.perf_counter() - start_ts) * 1000)
    try:
        out_path = Path(args.out)
        if out_path.parent and not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        lint_warns, _ = lint_json_file(out_path, "sidecar")
        status = "ok"
        if lint_warns:
            log(f"sidecar lint warnings: {lint_warns}", True, logger)
            status = "error" if args.strict else "ok"
        log(f"wrote sidecar payload -> {out_path}", args.verbose, logger)
        if os.getenv("LOG_JSON") == "1":
            log_stage_end(
                logger,
                "tempo_probe",
                status=status,
                audio=args.audio,
                out=args.out,
                duration_ms=duration_ms,
                selected_backend=backend,
                backend=result.get("backend", backend),
                beats_count=len(result.get("beats_sec") or []),
                warnings=lint_warns,
            )
            logger("end", {"event": "end", "audio": args.audio, "out": args.out, "tool": "tempo_sidecar", "status": status, "backend": backend, "duration_ms": duration_ms, "warnings": lint_warns})
        if status == "error":
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001
        log(f"failed to write sidecar payload to {args.out}: {exc}", True, logger)
        if os.getenv("LOG_JSON") == "1":
            log_stage_end(logger, "tempo_probe", status="error", audio=args.audio, out=args.out, selected_backend=backend, reason=str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
