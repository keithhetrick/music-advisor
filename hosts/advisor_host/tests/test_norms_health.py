from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_payload


def test_health_warns_when_no_norms():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    # ask health
    resp = handle_message(session, "health")
    assert resp["ui_hints"]
    # should mention missing norms
    warnings = resp["ui_hints"].get("warnings") or []
    assert any("no market_norms" in w.lower() or "no norms" in w.lower() for w in warnings) or (
        "No analysis" in resp["reply"]
    )
