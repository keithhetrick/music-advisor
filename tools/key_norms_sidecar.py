"""Compatibility shim delegating to shared.ma_utils.key_norms_sidecar."""
from shared.ma_utils.key_norms_sidecar import (
    KeyAdvisory,
    KeyLaneStats,
    KeySongPlacement,
    SongKey,
    build_key_advisory,
    build_sidecar_payload,
    compute_lane_stats,
    compute_song_placement,
    derive_out_path,
    format_key_name,
    load_lane_keys,
    main,
    resolve_song_key,
)

__all__ = [
    "KeyAdvisory",
    "KeyLaneStats",
    "KeySongPlacement",
    "SongKey",
    "build_key_advisory",
    "build_sidecar_payload",
    "compute_lane_stats",
    "compute_song_placement",
    "derive_out_path",
    "format_key_name",
    "load_lane_keys",
    "main",
    "resolve_song_key",
]
