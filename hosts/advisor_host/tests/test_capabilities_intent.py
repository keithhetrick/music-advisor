from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_payload


def test_capabilities_intent():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    # capabilities/help intent
    resp = handle_message(session, "what can you do?")
    assert resp["ui_hints"]["quick_actions"]
    assert resp["reply"]
