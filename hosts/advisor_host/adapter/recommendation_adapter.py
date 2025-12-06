"""
Adapter layer for recommendation/optimization engine.

Keeps host coupling minimal: host calls adapter.run(payload, norms) and
adapter.run_advisory(payload) for non-norms flow.

Supports future remote mode: set REC_ENGINE_MODE=remote and REC_ENGINE_URL to
call an HTTP endpoint instead of the local engine. Defaults to local.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional

from advisor_host.adapter.engine_contract import validate_engine_response
from advisor_host.host.advisor import run_advisory, run_recommendation


def _post_remote(url: str, payload: Dict[str, Any], norms: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"payload": payload}
    if norms is not None:
        body["norms"] = norms
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(payload: Dict[str, Any], norms: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run recommendation with optional norms. Returns the engine output dict.
    """
    mode = os.getenv("REC_ENGINE_MODE", "local").lower()
    if mode == "remote":
        url = os.getenv("REC_ENGINE_URL")
        if not url:
            raise RuntimeError("REC_ENGINE_URL is required when REC_ENGINE_MODE=remote")
        resp = _post_remote(url, payload, norms)
    else:
        resp = run_recommendation(payload, norms)
    validate_engine_response(resp)
    return resp


def run_without_norms(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advisory-only (no norms) run.
    """
    mode = os.getenv("REC_ENGINE_MODE", "local").lower()
    if mode == "remote":
        url = os.getenv("REC_ENGINE_URL")
        if not url:
            raise RuntimeError("REC_ENGINE_URL is required when REC_ENGINE_MODE=remote")
        resp = _post_remote(url, payload, None)
    else:
        resp = run_advisory(payload)
    validate_engine_response(resp)
    return resp


__all__ = ["run", "run_without_norms"]
