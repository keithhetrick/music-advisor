"""
Playback-style E2E: use precomputed sample client + HCI to simulate a full flow
without running the extractor/sidecars. Posts to chat handler directly (no HTTP).
"""
from __future__ import annotations
# ruff: noqa: I001

import json
from pathlib import Path

import pytest

from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.engine.recommendation import compute_recommendation
from recommendation_engine.tests.fixtures import sample_market_norms


def load_payload(rel_path: str) -> dict:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / rel_path).read_text())


@pytest.mark.parametrize(
    "client_rel,hci_rel",
    [
        ("docs/samples/chat_analyze_sample.json", None),
        ("docs/samples/chat_analyze_experimental.json", None),
        ("docs/samples/chat_analyze_strong_historical.json", None),
    ],
)
def test_playback_analyze_then_structure(client_rel: str, hci_rel: str | None):
    # These samples already include payload+norms; we use the payload directly.
    merged = load_payload(client_rel)
    payload = merged.get("payload") or merged  # samples are wrapped as chat-ready
    norms = merged.get("norms") or sample_market_norms

    # Compute recommendation via engine (direct) to ensure engine still accepts the sample
    _ = compute_recommendation(payload, norms)

    # Host-level flow
    session = ChatSession()
    intro = handle_message(session, "analyze", payload=payload, market_norms_snapshot=norms)
    assert intro["ui_hints"]["show_cards"]
    follow = handle_message(session, "structure")
    assert follow["ui_hints"]["show_cards"]
    assert follow["session_id"] == session.session_id
