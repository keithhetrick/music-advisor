#!/usr/bin/env python3
import argparse, json, os, re, tempfile
from pathlib import Path
from collections import defaultdict

from ma_audio_engine.adapters.bootstrap import ensure_repo_root
from ma_config.paths import get_calibration_root, get_repo_root

ensure_repo_root()
import sys  # noqa: E402

ROOT = get_repo_root()
CALIB_DIR_DEFAULT = get_calibration_root() / "audio"

FIT_FOLDERS = [
    "00_core_modern",
    "01_echo_85_95",
    "02_echo_00_10",
    "03_echo_10_14",
    "04_echo_15_19",
    "05_echo_20_24",
]

EVAL_FOLDERS_OPTIONAL = [
    "13_negatives_core",
    "14_negatives_memes",
    "99_holdout_eval",
]

# YYYY_Artist_Title__album.wav   (underscores only)
NAME_RX = re.compile(
    r"^(?P<year>\d{4})_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*__(album|single)\.(wav|aiff|aif|flac|mp3)$",
    re.IGNORECASE,
)

AUDIO_EXTS = {".wav", ".aiff", ".aif", ".flac", ".mp3"}

from ma_audio_engine.adapters import add_log_sandbox_arg, apply_log_sandbox_env
from ma_audio_engine.adapters import make_logger
from ma_audio_engine.adapters import utc_now_iso
from shared.security import subprocess as sec_subprocess
from shared.security.config import CONFIG as SEC_CONFIG

def iter_audio_files(folder: Path):
    for p in sorted(folder.glob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p

def run_features(pybin: Path, audio_path: Path, out_json: Path) -> dict:
    """Run ma_audio_features.py and read the output JSON."""
    cmd = [str(pybin), str(ROOT / "ma_audio_features.py"), str(audio_path), "-o", str(out_json)]
    sec_subprocess.run_safe(
        cmd,
        allow_roots=SEC_CONFIG.allowed_binary_roots,
        timeout=SEC_CONFIG.subprocess_timeout,
        check=True,
    )
    return json.loads(out_json.read_text())

def main():
    ap = argparse.ArgumentParser(description="Calibration readiness checker")
    ap.add_argument("--root", default=str(CALIB_DIR_DEFAULT), help="calibration audio root")
    ap.add_argument("--report", default=str(get_calibration_root() / "report.json"))
    ap.add_argument("--csv", default=str(get_calibration_root() / "report.csv"))
    ap.add_argument("--fast", action="store_true", help="skip feature extraction (naming & counts only)")
    ap.add_argument("--venv-python", default=str(ROOT / ".venv" / "bin" / "python3"))
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
    redact_env = os.getenv("LOG_REDACT", "0") == "1"
    redact_values_env = [v for v in (os.getenv("LOG_REDACT_VALUES") or "").split(",") if v]
    redact_flag = args.log_redact or redact_env
    secrets = (
        [v for v in (args.log_redact_values.split(",") if args.log_redact_values else []) if v]
        or redact_values_env
    )
    log = make_logger("calibration_readiness", use_rich=False, redact=redact_flag, secrets=secrets)

    calib_root = Path(args.root)
    pybin = Path(args.venv_python)

    # 1) folder existence
    missing = [f for f in FIT_FOLDERS if not (calib_root / f).exists()]
    # Optional folders are not required; just note their presence if exist.

    # 2) file discovery + validations
    summary = {"folders": {}, "errors": [], "warnings": []}
    all_basenames = set()
    dupes = []

    targets = FIT_FOLDERS + [f for f in EVAL_FOLDERS_OPTIONAL if (calib_root / f).exists()]
    for folder_name in targets:
        fpath = calib_root / folder_name
        if not fpath.exists():
            continue
        files = list(iter_audio_files(fpath))
        summary["folders"][folder_name] = {"count": len(files), "files": [x.name for x in files]}
        # Count checks
        if folder_name in FIT_FOLDERS:
            if len(files) < 8:
                summary["errors"].append(f"{folder_name}: has {len(files)} (<8 minimum)")
            elif len(files) < 10:
                summary["warnings"].append(f"{folder_name}: has {len(files)} (aim for 10+)")

        # Naming checks + dupes
        for af in files:
            if not NAME_RX.match(af.name):
                summary["warnings"].append(f"{folder_name}: bad name format: {af.name}")
            base = af.stem  # without extension
            if base in all_basenames:
                dupes.append(str(af))
            else:
                all_basenames.add(base)

    if missing:
        summary["errors"].append(f"Missing required folders: {', '.join(missing)}")

    if dupes:
        summary["errors"].append(f"Duplicate base names found: {dupes}")

    # 3) features (optional heavy)
    feats = defaultdict(list)
    if not args.fast:
        tmpdir = Path(tempfile.mkdtemp(prefix="calib_feats_"))
        for folder_name, info in summary["folders"].items():
            for fname in info["files"]:
                af = calib_root / folder_name / fname
                try:
                    out_json = tmpdir / (af.stem + ".features.json")
                    d = run_features(pybin, af, out_json)
                    # Pick the most important fields we expect to be non-null for readiness
                    tempo = d.get("tempo_bpm") or (d.get("features_full") or {}).get("bpm")
                    dur = d.get("runtime_sec") or (d.get("features_full") or {}).get("duration_sec")
                    feats[folder_name].append({
                        "file": af.name,
                        "tempo_bpm": tempo,
                        "duration_sec": dur,
                        "loudness_lufs": (d.get("features_full") or {}).get("loudness_lufs"),
                        "energy": (d.get("features_full") or {}).get("energy"),
                        "danceability": (d.get("features_full") or {}).get("danceability"),
                        "valence": (d.get("features_full") or {}).get("valence"),
                    })
                    if tempo is None or dur is None:
                        summary["warnings"].append(f"{folder_name}: {af.name} has null tempo/duration (check extract).")
                except Exception as e:
                    summary["errors"].append(f"{folder_name}: feature parse error for {af.name}: {e}")

    summary["features"] = feats

    # Write reports
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2))

    # CSV (simple)
    csv_rows = ["folder,file,tempo_bpm,duration_sec,loudness_lufs,energy,danceability,valence"]
    for folder_name, rows in feats.items():
        for r in rows:
            csv_rows.append(",".join([
                folder_name,
                r["file"],
                str(r.get("tempo_bpm") or ""),
                str(r.get("duration_sec") or ""),
                str(r.get("loudness_lufs") or ""),
                str(r.get("energy") or ""),
                str(r.get("danceability") or ""),
                str(r.get("valence") or ""),
            ]))
    Path(args.csv).write_text("\n".join(csv_rows))

    # Console summary
    log("\n== Calibration Readiness ==")
    log(f"Root: {calib_root}")
    if summary["errors"]:
        log("ERRORS:")
        for e in summary["errors"]:
            log(f"  - {e}")
    if summary["warnings"]:
        log("WARNINGS:")
        for w in summary["warnings"]:
            log(f"  - {w}")

    log("\nCounts:")
    for folder_name in FIT_FOLDERS:
        c = summary["folders"].get(folder_name, {}).get("count", 0)
        log(f"  {folder_name}: {c} files")

    log(f"\nReport written: {report_path}")
    log(f"CSV written: {args.csv}")
    log(f"[DONE] Finished at {utc_now_iso()}")
    return 1 if summary["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
