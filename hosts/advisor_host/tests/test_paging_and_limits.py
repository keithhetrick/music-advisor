import json

from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def test_history_byte_cap_truncates():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    # simulate many messages to blow past history cap
    for _ in range(30):
        handle_message(session, "groove?", payload=None, market_norms_snapshot=None)
    assert len(json.dumps(session.history)) <= int(__import__("os").getenv("HOST_MAX_HISTORY_BYTES", "65536"))


def test_reply_truncation():
    session = ChatSession()
    # Force a long reply by asking for mood multiple times
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    resp = handle_message(session, "mood? " * 200)
    # reply should exist and be within cap
    max_bytes = int(__import__("os").getenv("HOST_MAX_REPLY_BYTES", "8192"))
    assert len(resp["reply"].encode("utf-8")) <= max_bytes + 3  # allow ellipsis


def test_paging_no_more_warning():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    # page until _more false
    last_resp = None
    for _ in range(10):
        last_resp = handle_message(session, "optimization?", payload=None, market_norms_snapshot=None)
    assert last_resp
    assert "warnings" in last_resp["ui_hints"]


def test_auth_missing_returns_401_via_provider():
    from advisor_host.auth.auth import AuthError
    from advisor_host.auth.providers import StaticBearerAuthProvider
    provider = StaticBearerAuthProvider("secret")
    try:
        provider.verify({"Authorization": "wrong"})
        raise AssertionError("expected auth failure")
    except AuthError:
        pass
