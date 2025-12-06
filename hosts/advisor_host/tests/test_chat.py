from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def test_handle_message_with_payload_and_norms():
    session = ChatSession()
    intro = handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    assert intro["ui_hints"]["show_cards"]
    # follow-up query should use last recommendation
    reply = handle_message(session, "how is the groove?")
    assert "groove" in reply["reply"].lower() or reply["ui_hints"]["show_cards"]


def test_handle_message_without_norms_warns():
    session = ChatSession()
    intro_resp = handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    assert "no market_norms" in intro_resp["reply"]
    # follow-up still works
    reply = handle_message(session, "tell me more")
    assert reply["session_id"] == session.session_id


def test_paging_axes_and_history():
    session = ChatSession()
    first_resp = handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    assert first_resp["session_id"] == session.session_id
    first = handle_message(session, "loudness?")
    assert "Loudness" in first["reply"] or "loudness" in first["reply"].lower()
    more = handle_message(session, "more")
    assert more["session_id"] == session.session_id
    assert session.history  # history being tracked


def test_profile_hints():
    session = ChatSession(host_profile_id="producer_advisor_v1")
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=None)
    reply = handle_message(session, "structure")
    ui = reply["ui_hints"]
    assert "tone" in ui
    assert "primary_slices" in ui


def test_tutorial_and_dynamic_quick_actions():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    tutorial_reply = handle_message(session, "tutorial")
    qa = tutorial_reply["ui_hints"]["quick_actions"]
    assert any(q.get("intent") == "health" for q in qa)


def test_compare_quick_action_when_prev_exists():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    handle_message(session, "analyze again", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    reply = handle_message(session, "compare")
    qa = reply["ui_hints"]["quick_actions"]
    assert any(q.get("intent") == "compare" for q in qa)


def test_ui_hints_present_for_core_intents():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    intents = ["structure", "groove", "loudness", "mood", "historical", "optimize", "plan"]
    for intent in intents:
        resp = handle_message(session, intent)
        ui = resp["ui_hints"]
        # show_cards or quick_actions should be present; errors would throw before this
        assert "show_cards" in ui
        assert "quick_actions" in ui
        # narrative should not be empty
        assert resp["reply"], f"{intent} should include narrative"
