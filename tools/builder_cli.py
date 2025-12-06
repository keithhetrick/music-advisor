#!/usr/bin/env python3
"""
tools/builder_cli.py — Builder CLI for Quick Action / local use.

- Creates YYYY/MM/DD/<slug>/ under --output-root.
- (HOOKS) Call your real feature extractors here (when ready).
- Assembles a *.pack.json + *.client.txt using whatever artifacts exist.
- Prints OUTDIR=<path> so the wrapper can continue.

Minimal viable fields we try to fill:
  runtime_sec, tempo_bpm, tempo_band_bpm, ttc_sec, exposures
"""
import argparse, json, os, re, sys, pathlib
from datetime import datetime
from typing import Any, Dict, Optional
from tools import names

Path = pathlib.Path

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s

def read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

def derive_tempo_band(tempo: Optional[float]) -> Optional[str]:
    if not tempo:
        return None
    # integer buckets: 80–89, 90–99, 100–109, 110–119, 120–129, ...
    i = int(round(tempo))
    low = (i // 10) * 10
    high = low + 9
    return f"{low}\u2013{high}"

def pick_latest(glob: str, root: Path) -> Optional[Path]:
    files = sorted(root.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()

    audio = Path(args.audio).expanduser().resolve()
    if not audio.exists():
        print(f"ERROR: audio not found: {audio}", file=sys.stderr)
        sys.exit(66)

    output_root = Path(args.output_root).expanduser().resolve()
    today = datetime.now().strftime("%Y/%m/%d")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    stem = audio.stem
    slug = slugify(stem)
    outdir = output_root.joinpath(today, slug)
    outdir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # HOOKS: when you’re ready, run your real extractors BEFORE assembly
    #   run_features(audio, outdir)
    #   run_lyrics(audio, outdir)
    #   run_beatlink(audio, outdir)
    #   run_merge(outdir)
    #
    # For now we’re in “assemble what exists” mode.
    # ------------------------------------------------------------------

    # Try to find artifacts produced by other flows (drag-and-drop, etc.)
    features_p = pick_latest("*features.json", outdir)
    beatlink_p = pick_latest("*beatlink.json", outdir)
    merged_p   = pick_latest("*merged.json", outdir)

    features = read_json(features_p) if features_p else None
    beatlink = read_json(beatlink_p) if beatlink_p else None
    merged   = read_json(merged_p) if merged_p else None

    # Pull fields if present in typical shapes you’ve been using
    runtime_sec = None
    tempo_bpm   = None
    ttc_sec     = None
    exposures   = None

    # Try features.json
    if isinstance(features, dict):
        # common keys seen in your outputs
        runtime_sec = features.get("runtime_sec") or features.get("duration") or runtime_sec
        tempo_bpm   = features.get("tempo_bpm")   or features.get("tempo")     or tempo_bpm

    # Try beatlink.json (if it tracks tempo/sections)
    if isinstance(beatlink, dict):
        tempo_bpm   = beatlink.get("tempo_bpm")   or tempo_bpm
        runtime_sec = beatlink.get("runtime_sec") or runtime_sec
        # if you track hook or TTC in beatlink:
        ttc_sec     = beatlink.get("ttc_sec")     or ttc_sec

    # If merged has a canonical place for these, prefer that
    if isinstance(merged, dict):
        mvp = merged.get("MVP") or {}
        runtime_sec = mvp.get("runtime_sec") or runtime_sec
        tempo_bpm   = mvp.get("tempo_bpm")   or tempo_bpm
        ttc_sec     = mvp.get("ttc_sec")     or ttc_sec
        exposures   = mvp.get("exposures")   or exposures

    # As a last resort, you can regex the filename for a tempo hint (optional)
    tempo_band_bpm = derive_tempo_band(tempo_bpm)
    if tempo_band_bpm is None:
        # rough guess from filename like "... 118 bpm ..."
        m = re.search(r'(\d{2,3})\s*bpm', slug)
        if m:
            tempo_bpm = tempo_bpm or float(m.group(1))
            tempo_band_bpm = derive_tempo_band(tempo_bpm)

    # Build pack object
    pack_obj = {
        "MVP": {
            "region": "US",
            "runtime_sec": runtime_sec,
            "tempo_bpm": tempo_bpm,
            "tempo_band_bpm": tempo_band_bpm,
            "ttc_sec": ttc_sec,
            "exposures": exposures,
            "MARKET_NORMS": {"profile": "Pop"},
        },
        # If merged has a 'features' block, pass it through for advisory detail
        "merged": merged.get("features") and {"features": merged["features"]} if isinstance(merged, dict) else {
            "features": {
                "rhythm": {},
                "production": {},
                "tonal": {}
            }
        }
    }

    # Write pack + client helper
    pack = outdir.joinpath(f"{slug}_{ts}.pack.json")
    pack.write_text(json.dumps(pack_obj, ensure_ascii=False), encoding="utf-8")

    tempo_band_for_header = pack_obj["MVP"]["tempo_band_bpm"] or "null"
    client_body = f"""# Music Advisor — Auto by builder_cli.py
# STRUCTURE_POLICY: mode=optional | reliable=false | use_ttc=false | use_exposures=false
# GOLDILOCKS_POLICY: active=true | priors={{'Market': 0.5, 'Emotional': 0.5}} | caps={{'Market': 0.58, 'Emotional': 0.58}}
/audio map pack region=US profile=Pop

# MVP (effective for scoring)
# TempoBand={tempo_band_for_header}  TTC={'null' if ttc_sec is None else ttc_sec}  Runtime={'null' if runtime_sec is None else runtime_sec}  Exposures={'null' if exposures is None else exposures}
/advisor ingest
/advisor run full
/advisor export summary
"""
    client_path = outdir.joinpath(f"{slug}_{ts}{names.client_txt_suffix()}")
    client_path.write_text(client_body, encoding="utf-8")

    print(f"[builder] OUTDIR={outdir}")
    print(f"OUTDIR={outdir}")  # machine-readable for wrapper

if __name__ == "__main__":
    main()
