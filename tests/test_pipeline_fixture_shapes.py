"""
Synthetic pipeline fixture sanity check.

These fixtures model the *shape* of a successful run (payload → advisory → host
response) without embedding real data. They serve as a single point of reference
for what “success” looks like to readers and downstream tooling.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "pipeline_sample"


def _load(name: str):
    return json.loads((FIXTURE_ROOT / name).read_text())


def test_sample_payload_shape():
    payload = _load("sample_payload.json")
    assert "audio" in payload and "features" in payload["audio"]
    feats = payload["audio"]["features"]
    for key in ("tempo", "key", "mode", "audio_axes"):
        assert key in feats
    assert payload.get("qa", {}).get("status") == "pass"
    assert payload.get("run", {}).get("round") == 3


def test_sample_advisory_shape():
    adv = _load("sample_advisory.json")["Baseline"]
    assert adv["canonical_hci_source"] == "audio_axes"
    assert isinstance(adv.get("axes"), list) and adv["axes"]
    assert "advisory" in adv


def test_sample_host_response_shape():
    resp = _load("sample_host_response.json")
    for key in ("canonical_hci", "axes", "historical_echo", "optimization"):
        assert key in resp
    assert isinstance(resp["optimization"], list)

