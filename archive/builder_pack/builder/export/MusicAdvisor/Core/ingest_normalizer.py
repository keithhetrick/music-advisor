# MusicAdvisor/Core/ingest_normalizer.py
from __future__ import annotations
import json, re, fnmatch
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Iterable

# ---------- low-level helpers ----------

def _load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

def _glob_one(d: Path, patterns: Iterable[str]) -> Optional[Path]:
    """Return the first file matching any of the patterns (fnmatch) inside dir d."""
    for pat in patterns:
        for child in sorted(d.iterdir()):
            if child.is_file() and fnmatch.fnmatch(child.name, pat):
                return child
    return None

def _sibling_files(pack_path: Path) -> Dict[str, Path]:
    """
    Be permissive: accept either <stem>.<type>.json or *.<type>.json variants.
    Targets:
      - features (.features.json, *features*.json)
      - merged   (.merged.json, *merged*.json)
      - beatlink (.beatlink.json, *beat*.json)
      - lyrics   (.lyrics.json, *lyrics*.json)
      - lyric_axis (.lyric_axis.json, *lyric_axis*.json, *axis*.json)
    """
    d = pack_path.parent
    stem = pack_path.name.split(".pack.json")[0]
    out: Dict[str, Path] = {}

    exact = {
        "features": d / f"{stem}.features.json",
        "merged": d / f"{stem}.merged.json",
        "beatlink": d / f"{stem}.beatlink.json",
        "lyrics": d / f"{stem}.lyrics.json",
        "lyric_axis": d / f"{stem}.lyric_axis.json",
    }
    for k, p in exact.items():
        if p.exists():
            out[k] = p
    if out:
        return out

    # fallback glob (order: most specific -> general)
    globs = {
        "features": ["*.features.json", "*features*.json"],
        "merged": ["*.merged.json", "*merged*.json"],
        "beatlink": ["*.beatlink.json", "*beat*.json"],
        "lyrics": ["*.lyrics.json", "*lyrics*.json"],
        "lyric_axis": ["*.lyric_axis.json", "*lyric_axis*.json", "*axis*.json"],
    }
    for k, pats in globs.items():
        hit = _glob_one(d, pats)
        if hit:
            out[k] = hit
    return out

def _parse_helper_region_profile(helper_txt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract region + MARKET_NORMS.profile from lines like:
      /audio map pack region=US profile=Pop
    """
    region = None
    profile = None
    for line in helper_txt.splitlines():
        if "/audio map pack" in line:
            m_r = re.search(r"region\s*=\s*([A-Za-z_-]+)", line)
            m_p = re.search(r"profile\s*=\s*([A-Za-z0-9._-]+)", line)
            if m_r: region = m_r.group(1)
            if m_p: profile = m_p.group(1)
    return region, profile

def _tempo_band_from_bpm(bpm: Optional[float]) -> Optional[str]:
    if bpm is None:
        return None
    try:
        b = float(bpm)
    except Exception:
        return None
    lo = int(b // 10) * 10
    hi = lo + 9
    return f"{lo}–{hi}"

def _pick_first(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (str, int, float)) and v == "":
            continue
        return v
    return None

def _dig(d: Optional[dict], path: str) -> Any:
    """path like 'a.b.c' -> returns value or None"""
    cur = d or {}
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def _first_key(dct: Optional[dict], *paths: str) -> Any:
    for p in paths:
        v = _dig(dct, p)
        if v is not None:
            return v
    return None

# ---------- lyric fallbacks ----------

def _first_chorus_time_from_lyrics(lyrics_json: dict) -> Optional[float]:
    """Heuristic: first section tagged CHORUS/HOOK/REFRAIN, use its 'start'/'t0' (sec)."""
    try:
        secs = lyrics_json.get("section_timestamps") or []
        for s in secs:
            tag = (s.get("tag") or "").upper()
            if tag in ("CHORUS", "HOOK", "REFRAIN"):
                return float(s.get("start") or s.get("t0"))
    except Exception:
        pass
    return None

def _chorus_exposure_count_from_lyrics(lyrics_json: dict) -> Optional[int]:
    """Heuristic: number of CHORUS/HOOK/REFRAIN sections."""
    try:
        secs = lyrics_json.get("section_timestamps") or []
        n = sum(1 for s in secs if (s.get("tag") or "").upper() in ("CHORUS","HOOK","REFRAIN"))
        if n:
            return int(n)
        text = (lyrics_json.get("text") or {}).get("sections") or []
        n = sum(1 for s in text if (s.get("tag") or "").upper() in ("CHORUS","HOOK","REFRAIN"))
        return int(n) if n else None
    except Exception:
        return None

# ---------- core ----------

def adapt_pack(pack_path: str | Path, helper_txt: str = "") -> Dict[str, Any]:
    pack_path = Path(pack_path)
    pack = _load_json(pack_path) or {}

    siblings = _sibling_files(pack_path)
    feats = _load_json(siblings.get("features", Path())) if "features" in siblings else None
    merged = _load_json(siblings.get("merged", Path())) if "merged" in siblings else None
    beat = _load_json(siblings.get("beatlink", Path())) if "beatlink" in siblings else None
    lyrics = _load_json(siblings.get("lyrics", Path())) if "lyrics" in siblings else None
    lyric_axis = _load_json(siblings.get("lyric_axis", Path())) if "lyric_axis" in siblings else None

    region, profile = _parse_helper_region_profile(helper_txt)

    # runtime
    rt = _pick_first(
        _first_key(pack,  "runtime_sec", "RuntimeSec", "mvp.runtime_sec", "meta.runtime_sec", "audio.runtime_sec", "duration_sec", "analysis.duration_sec"),
        _first_key(feats, "runtime_sec", "meter.runtime_sec", "durations.runtime_sec"),
        _first_key(merged, "runtime_sec"),
    )

    # tempo bpm
    tbpm = _pick_first(
        _first_key(pack,  "tempo_bpm", "mvp.tempo_bpm", "tempo.bpm", "analysis.tempo.bpm"),
        _first_key(feats, "tempo_bpm", "tempo.bpm", "analysis.tempo_bpm"),
        _first_key(beat,  "tempo_bpm", "tempo.bpm"),
        _first_key(merged,"tempo_bpm", "tempo.bpm"),
    )

    # ttc (real first; fallback to lyric-derived)
    ttc_real = _pick_first(
        _first_key(pack,   "ttc_sec", "mvp.ttc_sec"),
        _first_key(merged, "ttc_sec", "hooks.ttc_sec", "structure.ttc_sec"),
        _first_key(feats,  "structure.ttc_sec", "hooks.ttc_sec"),
    )
    ttc_lyr = _first_chorus_time_from_lyrics(lyrics or {})
    ttc = ttc_real if ttc_real is not None else ttc_lyr

    # exposures (real first; fallback to lyric-derived)
    exp_real = _pick_first(
        _first_key(pack,   "exposures", "mvp.exposures"),
        _first_key(merged, "exposures", "hooks.exposures", "structure.exposures"),
        _first_key(feats,  "structure.exposures", "hooks.exposures"),
    )
    exp_lyr = _chorus_exposure_count_from_lyrics(lyrics or {})
    exposures = exp_real if exp_real is not None else exp_lyr

    # sections & hooks
    sections = _pick_first(
        _first_key(pack, "sections"),
        _first_key(merged, "sections"),
        _first_key(feats, "structure.sections"),
    )
    hook_positions = _pick_first(
        _first_key(pack, "hook_positions"),
        _first_key(merged, "hook_positions"),
        _first_key(feats, "structure.hook_positions"),
    )

    # feature buckets
    rhythm_features     = _pick_first(_first_key(pack, "rhythm_features"),     _first_key(merged, "rhythm_features"),     _first_key(feats, "rhythm"))
    production_features = _pick_first(_first_key(pack, "production_features"), _first_key(merged, "production_features"), _first_key(feats, "production"))
    tonal_features      = _pick_first(_first_key(pack, "tonal_features"),      _first_key(merged, "tonal_features"),      _first_key(feats, "tonal"))
    era_refs            = _pick_first(_first_key(pack, "era_refs"),            _first_key(merged, "era_refs"))

    tempo_band = _tempo_band_from_bpm(tbpm) or _first_key(pack, "analysis.tempo.band", "tempo.band")

    mvp = {
        "region": region or pack.get("region") or _first_key(pack, "meta.region"),
        "runtime_sec": rt,
        "tempo_bpm": tbpm,
        "tempo_band_bpm": tempo_band,
        "ttc_sec": ttc,
        "exposures": exposures,
        "MARKET_NORMS": {"profile": profile or _first_key(pack, "MARKET_NORMS.profile", "meta.profile")},
    }

    buckets = {
        "sections": sections,
        "hook_positions": hook_positions,
        "rhythm_features": rhythm_features or {},
        "production_features": production_features or {},
        "tonal_features": tonal_features or {},
        "era_refs": era_refs,
        "lyrics": lyrics,
        "lyric_axis": lyric_axis,
        "beatlink": beat,
        "features_raw": feats,
        "pack_raw_passthrough": pack.get("pack_raw") if isinstance(pack.get("pack_raw"), dict) else None,
    }

    # provenance
    prov = {}
    def tag(key: str, src: str, value):
        if value is not None and key not in prov:
            prov[key] = src

    tag("runtime_sec", "pack/feats/merged", rt)
    tag("tempo_bpm", "pack/feats/beat/merged", tbpm)
    tag("tempo_band_bpm", "computed_from(tempo_bpm)", tempo_band)

    tag("ttc_sec", "pack/merged/feats.structure", ttc_real if ttc_real is not None else None)
    if ttc_real is None and ttc is not None:
        tag("ttc_sec", "derived_lyrics.first_chorus_start", ttc)

    tag("exposures", "pack/merged.hooks|feats.structure", exp_real if exp_real is not None else None)
    if exp_real is None and exposures is not None:
        tag("exposures", "derived_lyrics.chorus_count", exposures)

    tag("region", "helper.region|pack.region", mvp["region"])
    tag("MARKET_NORMS.profile", "helper.profile|pack.MARKET_NORMS.profile", mvp["MARKET_NORMS"]["profile"])
    tag("sections", "pack/merged/feats.structure.sections", sections)
    tag("hook_positions", "pack/merged/feats.structure.hook_positions", hook_positions)
    tag("rhythm_features", "pack/merged/feats.rhythm", rhythm_features)
    tag("production_features", "pack/merged/feats.production", production_features)
    tag("tonal_features", "pack/merged/feats.tonal", tonal_features)
    tag("era_refs", "pack/merged.era_refs", era_refs)

    expected_mvp = ["region","runtime_sec","tempo_bpm","tempo_band_bpm","ttc_sec","exposures","MARKET_NORMS.profile"]
    known_gaps = []
    for k in expected_mvp:
        if k == "MARKET_NORMS.profile":
            if not (mvp.get("MARKET_NORMS") or {}).get("profile"):
                known_gaps.append(k)
        elif mvp.get(k) is None:
            known_gaps.append(k)

    audit = {
        "provenance": prov,
        "sibling_sources": {k: str(v) for k, v in siblings.items()},
        "Known_Gaps": known_gaps,
    }

    return {"MVP": mvp, "Buckets": buckets, "Audit": audit}
