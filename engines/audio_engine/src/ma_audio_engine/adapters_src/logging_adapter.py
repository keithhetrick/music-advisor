"""
Logging adapter: helpers for consistent debug/info output with optional redaction/sandbox.

Config:
- Env: LOG_JSON=1 for structured logs; LOG_REDACT=1 to mask secrets; LOG_REDACT_VALUES=secret1,secret2 to redact.
- File: config/logging.json for prefix/redact defaults, sandbox trimming (drop beats/neighbors, max_chars).

This keeps emitters modular so callers can opt into structured/sandboxed logging
without rewriting print calls.

Usage:
- `log = make_logger(prefix="extractor", redact=True); log("message")`
- `slog = make_structured_logger(prefix="ranker", defaults={"tool":"hci"}); slog("event", {"status":"ok"})`
- `payload = sandbox_scrub_payload(payload, sandbox=sandbox_options())` when LOG_SANDBOX is enabled upstream.

Notes:
- Side effects: writes to stderr; sandbox scrubbing returns a new dict without mutating the input.
- Unknown env/config keys are ignored to keep behavior stable.
- Recommended patterns:
  - Structured logs: set LOG_JSON=1 or pass --log-json; consume with `make_structured_logger(...)`.
  - Redaction: enable LOG_REDACT/LOG_REDACT_VALUES to scrub secrets/paths; home paths are shortened to ~.
  - Sandbox: LOG_SANDBOX=1 enables beat/neighbor trimming; tune via config/logging.json (drop_beats, drop_neighbors, max_chars).
"""
from __future__ import annotations

import sys
from pathlib import Path
import json
import os
from typing import Callable, Optional

__all__ = [
    "LOG_REDACT",
    "LOG_REDACT_VALUES",
    "make_logger",
    "make_structured_logger",
    "sandbox_options",
    "sandbox_scrub_payload",
    "log_stage_start",
    "log_stage_end",
]

_CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "logging.json"

_DEFAULT_PREFIX = ""
_DEFAULT_REDACT = False
_DEFAULT_SECRETS = []
_DEFAULT_JSON = os.environ.get("LOG_JSON", "0") == "1"
_SANDBOX_CONFIG = {"enabled": False, "drop_beats": False, "drop_neighbors": False, "max_chars": None}

try:
    if _CFG_PATH.exists():
        data = json.loads(_CFG_PATH.read_text())
        if isinstance(data, dict):
            _DEFAULT_PREFIX = str(data.get("prefix", "")) if data.get("prefix") is not None else ""
            _DEFAULT_REDACT = bool(data.get("redact", False))
            secrets = data.get("secrets")
            if isinstance(secrets, list):
                _DEFAULT_SECRETS = [str(s) for s in secrets if s]
            sandbox = data.get("sandbox")
            if isinstance(sandbox, dict):
                _SANDBOX_CONFIG["enabled"] = bool(sandbox.get("enabled", False))
                _SANDBOX_CONFIG["drop_beats"] = bool(sandbox.get("drop_beats", False))
                _SANDBOX_CONFIG["drop_neighbors"] = bool(sandbox.get("drop_neighbors", False))
                max_chars = sandbox.get("max_chars")
                if isinstance(max_chars, int) and max_chars > 0:
                    _SANDBOX_CONFIG["max_chars"] = max_chars
except Exception:
# Logging config is optional; fall back silently.
    pass

# Env-level toggles used by some CLIs; exported via adapters facade for consistency.
LOG_REDACT = os.environ.get("LOG_REDACT", "0") == "1"
LOG_REDACT_VALUES = [
    v for v in os.environ.get("LOG_REDACT_VALUES", "").split(",") if v
]

def make_logger(prefix: str = "", redact: bool = False, secrets: Optional[list] = None, json_output: Optional[bool] = None) -> Callable[[str], None]:
    """
    Create a logger function. Optionally redact known secrets (naive string replace).
    """
    home = str(Path.home())
    pref = f"[{prefix or _DEFAULT_PREFIX}]" if (prefix or _DEFAULT_PREFIX) else ""
    redact = redact or _DEFAULT_REDACT
    secrets = secrets if secrets is not None else list(_DEFAULT_SECRETS)
    json_output = _DEFAULT_JSON if json_output is None else json_output

    def _log(msg: str) -> None:
        sanitized = msg.replace(home, "~")
        if redact:
            for s in secrets:
                if s:
                    sanitized = sanitized.replace(s, "***")
        if json_output:
            payload = {"prefix": pref.strip("[]") if pref else "", "message": sanitized}
            print(json.dumps(payload), file=sys.stderr)
        else:
            print(f"{pref} {sanitized}".strip(), file=sys.stderr)

    return _log


def make_structured_logger(prefix: str = "", defaults: Optional[dict] = None) -> Callable[[str, dict], None]:
    """
    Emit structured JSON logs with a consistent schema: {prefix,event,...fields}.
    Defaults are merged into each log line.
    """
    defaults = defaults or {}
    def _log(event: str, fields: Optional[dict] = None) -> None:
        payload = {"prefix": prefix, "event": event}
        payload.update(defaults)
        if fields:
            payload.update(fields)
        print(json.dumps(payload), file=sys.stderr)
    return _log


def sandbox_options() -> dict:
    """Return sandbox redaction options parsed from config/logging.json."""
    return dict(_SANDBOX_CONFIG)


def sandbox_scrub_payload(payload: dict, sandbox: Optional[dict] = None) -> dict:
    """
    Optionally scrub large blobs from the payload for sandboxed logging/exports.
    - drop_beats: remove tempo_beats_sec / beats_sec
    - drop_neighbors: remove neighbors lists (keeps neighbors_file path)
    - max_chars: truncate string fields longer than the limit
    """
    cfg = dict(_SANDBOX_CONFIG)
    if sandbox:
        cfg.update({k: v for k, v in sandbox.items() if k in cfg})
    if not cfg.get("enabled"):
        return payload
    data = dict(payload)
    if cfg.get("drop_beats"):
        for k in ("tempo_beats_sec", "beats_sec"):
            if k in data:
                data[k] = None
    if cfg.get("drop_neighbors"):
        for k in ("neighbors", "tier1_neighbors", "tier2_neighbors", "tier3_neighbors"):
            if k in data:
                data[k] = []
    max_chars = cfg.get("max_chars")
    if isinstance(max_chars, int) and max_chars > 0:
        for k, v in list(data.items()):
            if isinstance(v, str) and len(v) > max_chars:
                data[k] = v[:max_chars]
    return data


def log_stage_start(logger: Callable, stage: str, **fields) -> None:
    """
    Emit a stage_start event (structured if possible, fallback to plain text).
    Standard schema: event=stage_start, stage=<name>, extra fields (e.g., tool, version).
    """
    payload = {"stage": stage}
    payload.update(fields)
    try:
        logger("stage_start", payload)
    except TypeError:
        logger(f"[stage_start] stage={stage} {payload}")


def log_stage_end(logger: Callable, stage: str, status: str = "ok", **fields) -> None:
    """
    Emit a stage_end event with status/metrics. Matches stage_start schema.
    """
    payload = {"stage": stage, "status": status}
    payload.update(fields)
    try:
        logger("stage_end", payload)
    except TypeError:
        logger(f"[stage_end] stage={stage} status={status} {payload}")
