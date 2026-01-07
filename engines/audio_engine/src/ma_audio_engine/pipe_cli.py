from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from shared.security import subprocess as sec_subprocess
from shared.security.config import CONFIG as SEC_CONFIG

def main() -> None:
    ap = argparse.ArgumentParser(description="MusicAdvisor pipe: extract → host scorer → write advisory")
    ap.add_argument("--audio", required=True, help="Path to audio file")
    ap.add_argument("--out", required=False, default="advisory.json", help="Output advisory JSON")
    ap.add_argument("--sr", type=int, default=44100)
    ap.add_argument("--round", type=int, default=3)
    ap.add_argument("--axes", type=str, default=None, help="Override audio_axes (comma 6 floats)")
    ap.add_argument("--market", type=float, default=0.48)
    ap.add_argument("--emotional", type=float, default=0.67)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        tmp_root = Path(td)
        payload = tmp_root / "payload.json"
        cache_dir = tmp_root / "librosa_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        numba_cache = tmp_root / "numba_cache"
        numba_cache.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("LIBROSA_CACHE_DIR", str(cache_dir))
        env.setdefault("NUMBA_CACHE_DIR", str(numba_cache))
        # ensure we invoke the repo shims first (ma-extract/ma-pipe) and then the venv binaries
        venv_bin = str(Path(sys.executable).parent)
        repo_root = Path(__file__).resolve().parents[2]
        env["PATH"] = os.pathsep.join([str(repo_root), venv_bin, env.get("PATH", "")])

        extract_cmd = [
            sys.executable,
            "-m",
            "ma_audio_engine.extract_cli",
            "--audio",
            args.audio,
            "--out",
            str(payload),
            "--sr",
            str(args.sr),
            "--round",
            str(args.round),
        ]
        if args.axes:
            extract_cmd += ["--axes", args.axes]

        print(f"[ma-pipe] running: {' '.join(extract_cmd)}")
        sec_subprocess.run_safe(
            extract_cmd,
            allow_roots=SEC_CONFIG.allowed_binary_roots,
            timeout=SEC_CONFIG.subprocess_timeout,
            check=True,
        )

        host_cmd = [
            sys.executable,
            "-m",
            "ma_audio_engine.smoke",
            str(payload),
            "--market",
            str(args.market),
            "--emotional",
            str(args.emotional),
            "--round",
            str(args.round),
        ]
        print(f"[ma-pipe] running: {' '.join(host_cmd)}")
        out_proc = sec_subprocess.run_safe(
            host_cmd,
            allow_roots=SEC_CONFIG.allowed_binary_roots,
            timeout=SEC_CONFIG.subprocess_timeout,
            check=True,
            capture_output=True,
            text=True,
        )
        out = out_proc.stdout if out_proc.stdout is not None else ""

        disable_norms = env.get("MA_DISABLE_NORMS_ADVISORY", "") not in ("", "0", "false", "False")
        if disable_norms:
            try:
                data = json.loads(out)
                baseline = data.get("Baseline")
                if isinstance(baseline, dict) and "advisory" in baseline:
                    baseline.pop("advisory", None)
                out = json.dumps(data, indent=2)
            except Exception:
                pass

        Path(args.out).write_text(out)
        print(f"[ma-pipe] wrote {args.out}")

if __name__ == "__main__":
    main()
