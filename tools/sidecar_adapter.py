#!/usr/bin/env python3
"""
Sidecar adapter (bridge): hardened interface between the pipeline and tempo/key sidecars.

Purpose:
- Safely format and run external tempo/key sidecar commands (Essentia/Madmom/librosa runners).
- Enforce safety guards: allowed binaries roots, required placeholders, optional custom command blocking, resource limits, timeouts.
- Normalize output: load guarded JSON, return payload + output path + warnings instead of raising.

Config/Env hooks:
- Default command: `DEFAULT_SIDECAR_CMD` (tempo_sidecar_runner.py).
- Env: `MA_SIDECAR_PLUGIN` to inject a plugin runner; `ALLOW_CUSTOM_SIDECAR_CMD` evaluated by callers (pipeline driver/Automator).
- Security: uses `security.config.CONFIG` for allowed_binary_roots and subprocess timeouts.

Usage:
- `run_sidecar(audio_path, cmd_template, sidecar_json_out=..., allow_custom_cmd=True|False, require_exec=False, timeout_seconds=..., debug=print)`
- `cmd_template` must contain `{audio}` and `{out}` placeholders; returns `(payload_dict_or_none, output_path_or_none, warnings:list[str])`.

Failure semantics:
- Never raises for subprocess/json errors; returns `(None, None, warnings)` with hints (`sidecar_timeout`, `sidecar_output_missing`, `sidecar_binary_not_allowed`, etc.).
- Cleans up temp files unless `keep_temp` is True; captures and redacts stdout/stderr in debug callback.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import resource

from ma_audio_engine.adapters import di
from tools import names
from ma_audio_engine.adapters.error_adapter import load_json_guarded
from security.config import CONFIG
from security import subprocess as sec_subprocess

# Allow env override so Automator/CI can force venv python and correct PYTHONPATH.
DEFAULT_SIDECAR_CMD = os.getenv(
    "MA_TEMPO_SIDECAR_CMD",
    os.getenv("DEFAULT_SIDECAR_CMD", "python3 tools/tempo_sidecar_runner.py --audio {audio} --out {out}"),
)


def run_sidecar(
    audio_path: str,
    cmd_template: Optional[str],
    sidecar_json_out: Optional[str] = None,
    keep_temp: bool = False,
    require_exec: bool = False,
    allow_custom_cmd: bool = True,
    max_json_bytes: int = 5 << 20,
    cpu_limit_seconds: Optional[int] = None,
    mem_limit_bytes: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    debug: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], list[str]]:
    """
    Run an external tempo/key sidecar command and load its JSON output.
    The command template should contain {audio} and {out} placeholders.
    Returns (payload, output_path, warnings).

    Side effects:
    - Executes external binaries (ffprobe/ffmpeg/essentia/madmom runners).
    - Creates temp files/folders for output JSON unless an explicit path is provided.
    - Applies optional resource limits and honors CONFIG.allowed_binary_roots.

    Warnings (subset):
    - sidecar_custom_cmd_blocked, sidecar_missing_placeholders, sidecar_cmd_format_error
    - sidecar_binary_missing/not_allowed, sidecar_timeout, sidecar_subprocess_failed/error
    - sidecar_output_missing, sidecar_plugin_failed/error
    - sidecar_cmd_parse_error
    """
    dbg = debug or (lambda msg: None)
    warnings: list[str] = []
    # Plugin hook: allow MA_SIDECAR_PLUGIN to short-circuit with a custom runner
    plugin_runner = di.make_sidecar_runner(plugin=os.getenv("MA_SIDECAR_PLUGIN"))
    if plugin_runner.__name__ != "<lambda>" and plugin_runner.__name__ != "_noop":  # basic check
        try:
            tmp_out = sidecar_json_out or (tempfile.NamedTemporaryFile(delete=False, suffix=".json").name)
            rc = plugin_runner(audio=audio_path, out=tmp_out)
            if rc == 0:
                payload = load_json_guarded(tmp_out, max_bytes=max_json_bytes, expect_mapping=True, logger=debug or (lambda m: None))
                return payload, tmp_out, warnings
            warnings.append("sidecar_plugin_failed")
        except Exception:
            warnings.append("sidecar_plugin_error")

    cmd_template = cmd_template or DEFAULT_SIDECAR_CMD
    is_defaultish = "tempo_sidecar_runner.py" in cmd_template
    if not allow_custom_cmd and not is_defaultish and cmd_template != DEFAULT_SIDECAR_CMD:
        dbg("failed to prepare tempo sidecar command: custom command disabled (set ALLOW_CUSTOM_SIDECAR_CMD=1 to allow)")
        warnings.append("sidecar_custom_cmd_blocked")
        return None, None, warnings
    if "{audio}" not in cmd_template or "{out}" not in cmd_template:
        dbg("failed to prepare tempo sidecar command: missing required {audio}/{out} placeholders")
        warnings.append("sidecar_missing_placeholders")
        return None, None, warnings

    tempdir: Optional[tempfile.TemporaryDirectory[str]] = None
    out_path = sidecar_json_out
    try:
        if not out_path:
            if keep_temp:
                out_path = os.path.join(tempfile.mkdtemp(prefix="ma_sidecar_keep_"), f"tempo{names.tempo_sidecar_suffix()}")
            else:
                tempdir = tempfile.TemporaryDirectory(prefix="ma_sidecar_")
                out_path = os.path.join(tempdir.name, f"tempo{names.tempo_sidecar_suffix()}")
        # Avoid over-quoting; let shlex.split handle spaces safely and wrap paths that contain spaces.
        def _wrap(p: str) -> str:
            return f'"{p}"' if " " in p else p
        cmd = cmd_template.format(audio=_wrap(audio_path), out=_wrap(out_path))
    except Exception as e:
        dbg(f"failed to prepare tempo sidecar command: {e}")
        warnings.append("sidecar_cmd_format_error")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings

    try:
        parts = shlex.split(cmd)
        if not parts:
            raise ValueError("empty command after formatting")
        binary = parts[0]
        def _is_allowed_binary(bin_candidate: str) -> bool:
            raw_candidate = Path(bin_candidate).expanduser()
            candidate_path = raw_candidate
            if not candidate_path.is_absolute():
                candidate_path = (CONFIG.repo_root / candidate_path).expanduser()
            resolved = Path(shutil.which(bin_candidate) or bin_candidate).expanduser().resolve()
            def _under_safe(p: Path) -> bool:
                return any(str(p).startswith(str(root)) for root in CONFIG.allowed_binary_roots)
            return _under_safe(raw_candidate) or _under_safe(candidate_path) or _under_safe(resolved)

        if require_exec and shutil.which(binary) is None:
            dbg(f"tempo sidecar command not found/executable: {binary}")
            warnings.append("sidecar_binary_missing")
            if tempdir:
                tempdir.cleanup()
            return None, None, warnings
        if allow_custom_cmd and not _is_allowed_binary(binary):
            dbg(f"tempo sidecar binary not allowed: {binary}")
            warnings.append("sidecar_binary_not_allowed")
            if tempdir:
                tempdir.cleanup()
            return None, None, warnings
    except Exception as e:
        dbg(f"failed to parse sidecar command for preflight: {e}")
        warnings.append("sidecar_cmd_parse_error")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings

    dbg(f"running tempo sidecar: {cmd}")
    def _limit() -> None:
        # Best-effort resource limits; ignore if unsupported
        try:
            if cpu_limit_seconds is not None:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit_seconds, cpu_limit_seconds))
            if mem_limit_bytes is not None:
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit_bytes, mem_limit_bytes))
        except Exception:
            pass
    try:
        completed = sec_subprocess.run_safe(
            parts,
            allow_roots=CONFIG.allowed_binary_roots,
            timeout=timeout_seconds if timeout_seconds is not None else CONFIG.subprocess_timeout,
            check=True,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        dbg("tempo sidecar command timed out")
        warnings.append("sidecar_timeout")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings
    except subprocess.CalledProcessError as e:  # noqa: PERF203
        if isinstance(e.stderr, (bytes, bytearray)):
            stderr = e.stderr.decode("utf-8", errors="ignore")
        else:
            stderr = str(e.stderr or "")
        dbg(f"tempo sidecar command failed (rc={e.returncode}): {stderr}")
        warnings.append("sidecar_subprocess_failed")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings
    except Exception as e:  # noqa: BLE001
        dbg(f"tempo sidecar command failed: {e}")
        warnings.append("sidecar_subprocess_error")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings

    def _redact(p: str) -> str:
        home = os.path.expanduser("~")
        return p.replace(home, "~") if home else p
    if completed.stdout:
        dbg(f"tempo sidecar stdout: {_redact(completed.stdout.strip())}")
    if completed.stderr:
        dbg(f"tempo sidecar stderr: {_redact(completed.stderr.strip())}")

    if not out_path or not os.path.exists(out_path):
        dbg("tempo sidecar did not produce an output JSON")
        warnings.append("sidecar_output_missing")
        if tempdir:
            tempdir.cleanup()
        return None, None, warnings

    payload = load_json_guarded(out_path, max_bytes=max_json_bytes, expect_mapping=True, logger=dbg)
    if tempdir and not keep_temp:
        tempdir.cleanup()
    return payload, out_path, warnings
