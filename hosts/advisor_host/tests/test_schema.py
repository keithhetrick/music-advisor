from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def test_response_schema_shape():
    session = ChatSession()
    intro = handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    reply = handle_message(session, "groove?")
    for resp in (intro, reply):
        assert "session_id" in resp
        assert "reply" in resp
        assert "ui_hints" in resp
        ui = resp["ui_hints"]
        assert "show_cards" in ui
        assert "quick_actions" in ui
        assert "tone" in ui
