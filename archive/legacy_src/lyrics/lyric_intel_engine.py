#!/usr/bin/env python3
# lyrics/lyric_intel_engine.py
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict, Optional

def _read_json(p: str | Path) -> Dict[str, Any]:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}

def _clamp01(x: Optional[float]) -> float:
    try:
        v = float(x)
    except Exception:
        return 0.0
    return 0.0 if v < 0 else (1.0 if v > 1 else v)

def _nz(x: Optional[float], fallback: float = 0.0) -> float:
    try:
        return float(x) if x is not None else fallback
    except Exception:
        return fallback

def _norm_cap(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    v = (x - lo) / (hi - lo)
    if v < 0: v = 0.0
    if v > 1: v = 1.0
    return v

def _any_lyric_signal(hlm: Dict[str, Any], hli: Dict[str, Any]) -> bool:
    rd = _nz(hlm.get("rhyme_density"))
    rr = _nz(hlm.get("repetition_ratio"))
    pov = 1.0 if hlm.get("pov") else 0.0
    cad = 1.0 if hlm.get("cadence_class") else 0.0
    motifs = hlm.get("motif_taxonomy") or []
    sing = _nz(hli.get("singalong_prob"))
    talign_raw = hli.get("title_alignment")
    if isinstance(talign_raw, (int, float)): talign = _clamp01(talign_raw)
    elif isinstance(talign_raw, bool):       talign = 1.0 if talign_raw else 0.0
    else:                                    talign = 0.0
    secmap = hli.get("section_map") or {}
    hooks = 0.0
    if isinstance(secmap, dict):
        hooks = float(secmap.get("hook_repeats") or 0)
        sections = secmap.get("sections")
        if isinstance(sections, list) and hooks == 0.0:
            hooks = float(sum(1 for s in sections if str(s.get("tag","")).upper() in {"HOOK","CHORUS"}))
    return any([
        rd > 0, rr > 0, pov > 0, cad > 0, bool(motifs),
        sing > 0, hooks > 0, talign > 0
    ])

def _infer_vectors(hlm: Dict[str, Any], hli: Dict[str, Any]) -> Dict[str, float]:
    rhyme_density    = _clamp01(hlm.get("rhyme_density"))
    repetition_ratio = _clamp01(hlm.get("repetition_ratio"))
    motif_tax        = hlm.get("motif_taxonomy")
    motif_count      = float(len(motif_tax)) if isinstance(motif_tax, list) else 0.0
    pov_present      = 1.0 if hlm.get("pov") else 0.0
    cadence_present  = 1.0 if hlm.get("cadence_class") else 0.0
    era_fingerprint  = 1.0 if hlm.get("era_fingerprint") else 0.0

    singalong_prob   = _clamp01(hli.get("singalong_prob"))
    ta_raw           = hli.get("title_alignment")
    if isinstance(ta_raw, (int, float)):
        title_align = _clamp01(ta_raw)
    elif isinstance(ta_raw, bool):
        title_align = 1.0 if ta_raw else 0.0
    else:
        title_align = 0.0

    hook_repeats = 0.0
    secmap = hli.get("section_map") or {}
    if isinstance(secmap, dict):
        hook_repeats = float(secmap.get("hook_repeats") or 0)
        sections = secmap.get("sections")
        if isinstance(sections, list) and hook_repeats == 0.0:
            hook_repeats = float(sum(1 for s in sections if str(s.get("tag","")).upper() in {"HOOK","CHORUS"}))

    emotional = 0.45*singalong_prob + 0.35*repetition_ratio + 0.20*rhyme_density
    creative  = 0.55*rhyme_density + 0.30*_norm_cap(motif_count, 0, 6) + 0.15*cadence_present
    market    = 0.45*_norm_cap(hook_repeats, 0, 3) + 0.40*title_align + 0.15*repetition_ratio
    cultural  = 0.45*pov_present + 0.35*era_fingerprint + 0.20*cadence_present

    return {
        "Emotional": round(_clamp01(emotional), 3),
        "Creative":  round(_clamp01(creative),  3),
        "Market":    round(_clamp01(market),    3),
        "Cultural":  round(_clamp01(cultural),  3),
    }

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics", required=True, help="path to lyricflow JSON")
    ap.add_argument("--title", required=False, default=None)
    ap.add_argument("--genre", required=False, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    raw = _read_json(args.lyrics)
    prov = {
        "source": "Luminaire/HLM-HLI",
        "lang": raw.get("lang","en"),
        "confidence_overall": _nz(raw.get("confidence_overall"), 0.75),
        "ts": raw.get("ts")
    }
    hlm = raw.get("HLM") or {}
    hli = raw.get("HLI") or {}

    # Determine whether we truly have **no** usable lyric evidence
    no_signal = not _any_lyric_signal(hlm, hli)

    if no_signal:
        # Mark missing + apply conservative, non-zero floor so downstream never sees all-zero vectors
        vectors = {"Emotional": 0.12, "Creative": 0.10, "Market": 0.08, "Cultural": 0.06}
        flags = {"lyrics_missing": True, "translation_warning": bool(raw.get("translation_warning", False))}
        recs = ["Minimal lyric evidence detected (ASR/empty). Treat these lyric vectors as provisional."]
    else:
        vectors = _infer_vectors(hlm, hli)
        flags = {
            "lyrics_missing": False,
            "translation_warning": bool(raw.get("translation_warning", False))
        }
        recs = raw.get("recommendations") or []

    out = {
        "schema_version": "hlm_hli.1.0.2",
        "provenance": prov,
        "HLM": {
            "era_fingerprint": hlm.get("era_fingerprint"),
            "rhyme_density": _nz(hlm.get("rhyme_density")),
            "repetition_ratio": _nz(hlm.get("repetition_ratio")),
            "pov": hlm.get("pov"),
            "cadence_class": hlm.get("cadence_class"),
            "motif_taxonomy": hlm.get("motif_taxonomy"),
        },
        "HLI": {
            "hook_clarity_index": _nz(hli.get("hook_clarity_index")),
            "title_alignment": hli.get("title_alignment"),
            "singalong_prob": _nz(hli.get("singalong_prob")),
            "section_map": hli.get("section_map") or {},
        },
        "recommendations": recs,
        "vector_strengths": vectors,
        "flags": flags,
    }

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[lyric_intel_engine] wrote {outp}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
