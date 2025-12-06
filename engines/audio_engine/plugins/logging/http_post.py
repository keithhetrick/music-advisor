"""
Logging plugin that POSTs structured events to an HTTP endpoint.
Supports retries with exponential backoff and optional auth token/header.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from typing import Optional, Dict, Any


def factory(prefix: str = "", defaults: Optional[Dict[str, Any]] = None):
    defaults = defaults or {}
    endpoint = defaults.get("endpoint") or "http://localhost:5000/log"
    auth_token = defaults.get("auth_token")
    auth_scheme = defaults.get("auth_scheme", "Bearer")
    timeout = float(defaults.get("timeout", 1.0))
    max_retries = int(defaults.get("max_retries", 1))
    backoff_base = float(defaults.get("backoff_base", 0.25))
    backoff_max = float(defaults.get("backoff_max", 2.0))
    extra_headers = defaults.get("headers") or {}

    def _log(event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        payload = {"prefix": prefix, "event": event}
        payload.update(defaults or {})
        if fields:
            payload.update(fields)
        headers = {"Content-Type": "application/json"}
        headers.update(extra_headers)
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers)
        if auth_token:
            req.add_header("Authorization", f"{auth_scheme} {auth_token}")
        for attempt in range(max_retries):
            try:
                urllib.request.urlopen(req, timeout=timeout)
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    print(f"[logging.http_post] failed after {max_retries} attempts: {exc}", file=sys.stderr)
                    break
                if backoff_base > 0:
                    sleep_for = min(backoff_base * (2**attempt), backoff_max)
                    time.sleep(sleep_for)

    return _log
