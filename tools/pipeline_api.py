from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from tools.audio.ma_audio_features import analyze_pipeline, CLIP_PEAK_THRESHOLD, SILENCE_RATIO_THRESHOLD, LOW_LEVEL_DBFS_THRESHOLD
from tools.equilibrium_merge import merge_features
from tools.pack_writer import build_pack, build_client_helper_payload
from tools.ma_merge_client_and_hci import merge_client_hci
from tools.schema_utils import lint_json_file, lint_pack_payload, lint_merged_payload


def run_features(audio: str, *, tempo_sidecar_json_out: Optional[str] = None, require_sidecar: bool = False) -> Dict[str, Any]:
    """
    Run feature pipeline in-process and return result dict.

    Side effects:
    - Reads audio file; may invoke external sidecar if require_sidecar is True.
    - Raises FileNotFoundError for missing/empty audio.
    """
    audio_path = Path(audio)
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise FileNotFoundError(f"Audio file missing or empty: {audio_path}")
    return analyze_pipeline(
        path=audio,
        cache_dir=None,
        cache_backend=None,
        use_cache=False,
        force=True,
        clip_peak_threshold=CLIP_PEAK_THRESHOLD,
        silence_ratio_threshold=SILENCE_RATIO_THRESHOLD,
        low_level_dbfs_threshold=LOW_LEVEL_DBFS_THRESHOLD,
        fail_on_clipping_dbfs=None,
        external_tempo_json=None,
        tempo_backend="librosa.beat.beat_track" if not require_sidecar else "sidecar",
        tempo_sidecar_cmd=None,
        tempo_sidecar_json_out=tempo_sidecar_json_out,
        tempo_sidecar_keep=False,
        tempo_sidecar_verbose=False,
        tempo_sidecar_drop_beats=False,
        tempo_sidecar_conf_lower=None,
        tempo_sidecar_conf_upper=None,
        require_sidecar=require_sidecar,
    )


def run_merge(internal: Dict[str, Any], external: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], list[str]]:
    """Merge internal/external features and lint the merged payload (warnings only)."""
    merged = merge_features(internal, external)
    warns = lint_merged_payload(merged)
    return merged, warns


def run_pack(
    merged: Dict[str, Any],
    out_dir: Path,
    *,
    anchor: str = "00_core_modern",
    lyric_axis: Optional[Dict[str, Any]] = None,
    write_pack: bool = True,
    client_txt: Optional[Path] = None,
    client_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build pack + client helper payloads; optionally write pack/client artifacts.

    Side effects: writes pack/client files when requested; creates out_dir parents.
    """
    pack = build_pack(merged, audio_name=Path(merged.get("source_audio") or "audio").stem, anchor=anchor, lyric_axis=lyric_axis)
    lint_pack_payload(pack)
    if write_pack:
        pack_path = out_dir / f"{pack['audio_name']}.pack.json"
        pack_path.parent.mkdir(parents=True, exist_ok=True)
        pack_path.write_text(json.dumps(pack, indent=2))
    if client_txt:
        helper_payload = build_client_helper_payload(pack)
        clines = ["/audio import " + json.dumps(helper_payload, ensure_ascii=False), "", "/advisor ingest", "/advisor run full", "/advisor export summary"]
        client_txt.parent.mkdir(parents=True, exist_ok=True)
        client_txt.write_text("\n".join(clines) + "\n", encoding="utf-8")
    if client_json:
        client_json.parent.mkdir(parents=True, exist_ok=True)
        client_json.write_text(json.dumps(build_client_helper_payload(pack), indent=2), encoding="utf-8")
    return pack


def run_merge_client_hci(
    client_json: Dict[str, Any],
    hci_json: Dict[str, Any],
    tempo_overlay_block: Optional[str] = None,
    key_overlay_block: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, list[str]]:
    merged_client, rich_text, warns, _scores = merge_client_hci(
        client_json,
        hci_json,
        tempo_overlay_block=tempo_overlay_block,
        key_overlay_block=key_overlay_block,
    )
    return merged_client, rich_text, warns
