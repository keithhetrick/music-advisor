#!/usr/bin/env python3
import argparse, json, math, os
from pathlib import Path
from collections import Counter, defaultdict
from adapters.bootstrap import ensure_repo_root

ensure_repo_root()

from adapters import add_log_sandbox_arg, apply_log_sandbox_env
from adapters import make_logger
from adapters import utc_now_iso
from ma_config.paths import get_calibration_root
from shared.security import subprocess as sec_subprocess
from shared.security.config import CONFIG as SEC_CONFIG

LOG_REDACT = os.environ.get("LOG_REDACT", "1") == "1"
LOG_REDACT_VALUES = [v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v]
_log = make_logger("build_baseline_from_calibration", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)

# ---- Helpers ----

def find_audio_files(root: Path):
    exts = {".wav", ".aiff", ".aif", ".mp3", ".flac", ".m4a"}
    return [p for p in root.rglob("*") if p.suffix.lower() in exts]

def run_feature_extractor(repo_root: Path, audio_path: Path, out_json: Path):
    # Reuse your existing analyzer; only compute if missing
    if out_json.exists():
        return
    script = repo_root / "ma_audio_features.py"
    cmd = [sys.executable, str(script), str(audio_path), "-o", str(out_json)]
    sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=True,
    )

def read_feats(feat_json: Path):
    try:
        d = json.loads(feat_json.read_text())
    except Exception:
        return None
    # Normalize field names the builder expects
    tempo = d.get("tempo_bpm") or (d.get("features_full") or {}).get("bpm")
    key   = d.get("key") or (d.get("features_full") or {}).get("key")
    mode  = d.get("mode") or (d.get("features_full") or {}).get("mode")
    dur   = d.get("runtime_sec") or d.get("duration_sec") or (d.get("features_full") or {}).get("duration_sec")
    loud  = d.get("loudness_lufs") or (d.get("features_full") or {}).get("loudness_lufs")
    energy= d.get("energy") or (d.get("features_full") or {}).get("energy")
    dance = d.get("danceability") or (d.get("features_full") or {}).get("danceability")
    val   = d.get("valence") or (d.get("features_full") or {}).get("valence")
    meta  = d.get("meta") or {}
    year  = meta.get("year")
    return {
        "tempo": tempo, "key": key, "mode": mode, "runtime": dur, "loudness": loud,
        "energy": energy, "danceability": dance, "valence": val, "year": year
    }

def mean_std(vals):
    vals = [v for v in vals if v is not None and not math.isnan(v)]
    if not vals:
        return None, None
    m = sum(vals)/len(vals)
    if len(vals) == 1:
        return m, 0.0
    var = sum((x-m)**2 for x in vals)/(len(vals)-1)
    return m, math.sqrt(max(var, 0.0))

def in_band(bpm, lo, hi):
    return bpm is not None and lo <= bpm <= hi

def top_tempo_bands(bpm_values, bands, k=3):
    counts = []
    for lo, hi in bands:
        c = sum(1 for v in bpm_values if in_band(v, lo, hi))
        counts.append(((lo, hi), c))
    counts.sort(key=lambda x: x[1], reverse=True)
    return [f"{lo}–{hi}" for (lo, hi), _ in counts[:k]]

def year_from_filename(p: Path):
    # pull `__YYYY__` if present; else None
    parts = p.stem.split("__")
    for token in parts:
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None

# ---- Core ----

def collect_distribution(repo_root: Path, folder: Path):
    """Return list of per-file feature dicts; compute features if missing."""
    out = []
    for audio in find_audio_files(folder):
        feat_json = audio.with_suffix(".features.json")
        try:
            run_feature_extractor(repo_root, audio, feat_json)
        except Exception:
            # Try best-effort; skip failures
            continue
        d = read_feats(feat_json)
        if d is None:
            # attempt to inject year from filename if absent
            d = {}
        if d.get("year") is None:
            y = year_from_filename(audio)
            if y:
                d["year"] = y
        out.append(d)
    return out

def filter_by_year_bin(items, center_year, tol):
    lo, hi = center_year - tol, center_year + tol
    return [x for x in items if x.get("year") is not None and lo <= x["year"] <= hi]

def aggregate_stats(items):
    nums = defaultdict(list)
    keys = Counter()
    modes = Counter()
    for x in items:
        nums["tempo"].append(x.get("tempo"))
        nums["runtime"].append(x.get("runtime"))
        nums["loudness"].append(x.get("loudness"))
        nums["energy"].append(x.get("energy"))
        nums["danceability"].append(x.get("danceability"))
        nums["valence"].append(x.get("valence"))
        k = x.get("key"); m = x.get("mode")
        if k: keys[k] += 1
        if m: modes[m] += 1
    mu_sigma = {name: mean_std(vals) for name, vals in nums.items()}
    key_dist = {}
    total_keys = sum(keys.values())
    if total_keys:
        key_dist = {k: round(c/total_keys, 3) for k, c in keys.most_common()}
    mode_ratio = {}
    total_modes = sum(modes.values())
    if total_modes:
        mode_ratio = {k: round(c/total_modes, 3) for k, c in modes.items()}
    return mu_sigma, key_dist, mode_ratio, [v for v in nums["tempo"] if v is not None]

def mix(mu_modern, mu_echo, alpha):
    if mu_modern[0] is None and mu_echo[0] is None:
        return None, None
    m0, s0 = mu_modern
    m1, s1 = mu_echo
    if m0 is None: m0, s0 = m1, s1
    if m1 is None: m1, s1 = m0, s0
    a = alpha
    m = (1-a)*m0 + a*m1
    s = math.sqrt(max(((1-a)*(s0 or 0))**2 + (a*(s1 or 0))**2, 0.0))
    return m, s

def main():
    ap = argparse.ArgumentParser(description="Build MARKET_NORMS from calibration audio")
    ap.add_argument("--repo-root", default=".", help="path to music-advisor repo root")
    default_cfg = get_calibration_root() / "calibration_config.yaml"
    ap.add_argument("--config", default=str(default_cfg))
    ap.add_argument("--out", default="datahub/cohorts/US_Pop_Cal_Baseline_2025Q4.json")
    ap.add_argument(
        "--log-redact",
        action="store_true",
        help="Redact sensitive paths/values in logs (also honors env LOG_REDACT=1).",
    )
    ap.add_argument(
        "--log-redact-values",
        default=None,
        help="Comma list of extra values to redact in logs (also honors env LOG_REDACT_VALUES).",
    )
    add_log_sandbox_arg(ap)
    args = ap.parse_args()

    apply_log_sandbox_env(args)
    redact_flag = args.log_redact or LOG_REDACT
    redact_values = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or LOG_REDACT_VALUES
    )
    global _log
    _log = make_logger("build_baseline_from_calibration", redact=redact_flag, secrets=redact_values)

    try:
        import yaml
    except Exception:
        _log("Please `pip install pyyaml` in your venv.")
        return 2

    cfg = yaml.safe_load(Path(args.config).read_text())
    repo_root = Path(args.repo_root).resolve()
    core_modern = repo_root / cfg["paths"]["core_modern"]
    echo_root   = repo_root / cfg["paths"]["echo_root"]
    tol = int(cfg.get("bin_tolerance_years", 2))
    alpha = cfg["alpha"]

    # Collect modern
    items_modern = collect_distribution(repo_root, core_modern)
    mu_modern, key_modern, mode_modern, modern_bpms = aggregate_stats(items_modern)

    # Collect echo (concatenate bins; but enforce per-bin window)
    items_echo_all = []
    for b in cfg["echo_bins"]:
        year = int(b["year"])
        items_bin = filter_by_year_bin(collect_distribution(repo_root, echo_root / str(year)), year, tol)
        items_echo_all.extend(items_bin)
    mu_echo, key_echo, mode_echo, echo_bpms = aggregate_stats(items_echo_all)

    # Mix per axis
    mu_sig = {}
    for axis in ["tempo", "runtime", "loudness", "energy", "danceability", "valence"]:
        mu_sig[axis] = mix(mu_modern.get(axis, (None,None)), mu_echo.get(axis, (None,None)), float(alpha[axis]))

    # Keys + modes — mix by convex combination if both present
    def mix_cat(d0, d1, a):
        keys = set(d0) | set(d1)
        out = {}
        for k in keys:
            p0 = d0.get(k, 0.0); p1 = d1.get(k, 0.0)
            out[k] = (1-a)*p0 + a*p1
        s = sum(out.values()) or 1.0
        return {k: round(v/s, 3) for k, v in out.items()}

    a_keys = float(alpha["danceability"])  # categorical echo weight ~ feel axes
    key_dist = mix_cat(key_modern, key_echo, a_keys)

    a_modes = float(alpha["valence"])
    mode_ratio = mix_cat(mode_modern, mode_echo, a_modes)

    # Tempo bands preference (top-3)
    bands = [(lo, hi) for lo, hi in cfg["tempo_bands"]]
    band_prefs = top_tempo_bands([*modern_bpms, *echo_bpms], bands, k=3)

    # Assemble MARKET_NORMS
    norms = {
        "tempo_bpm_mean": round(mu_sig["tempo"][0], 2) if mu_sig["tempo"][0] is not None else None,
        "tempo_bpm_std":  round(mu_sig["tempo"][1], 2) if mu_sig["tempo"][1] is not None else None,
        "tempo_band_pref": band_prefs,
        "key_distribution": key_dist,
        "mode_ratio": mode_ratio,
        "runtime_sec_mean": round(mu_sig["runtime"][0], 2) if mu_sig["runtime"][0] is not None else None,
        "runtime_sec_std":  round(mu_sig["runtime"][1], 2) if mu_sig["runtime"][1] is not None else None,
    }

    out = {
        "id": cfg.get("baseline_id", "US_Pop_Cal_Baseline.json"),
        "region": cfg.get("region", "US"),
        "profile": cfg.get("profile", "Pop"),
        "MARKET_NORMS": norms,
        "source": {
            "core_modern_count": len(items_modern),
            "echo_count": len(items_echo_all),
            "echo_bins": [b["year"] for b in cfg["echo_bins"]],
            "alpha": cfg["alpha"],
        }
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    _log(f"[calibration] wrote {out_path} @ {utc_now_iso()}")

if __name__ == "__main__":
    sys.exit(main())
