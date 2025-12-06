from advisor_host.host.chat import ChatSession
from advisor_host.host.request_validation import RequestValidationError, validate_chat_request
from advisor_host.intents.intents import detect_intent, sanitize_quick_actions
from advisor_host.session.session_store import InMemorySessionStore, dict_to_session, session_to_dict


def test_detect_intent_prefers_keywords():
    assert detect_intent("please summarize and expand") == "summarize"
    assert detect_intent("tell me the groove and rhythm") == "groove"
    assert detect_intent("random text") == "general"
    # typo tolerance and aliases
    assert detect_intent("can you sumamrize this?") == "summarize"
    assert detect_intent("what about the groov and rhytm?") == "groove"
    assert detect_intent("tell me the loudnes info") == "loudness"


def test_quick_action_allowlist():
    actions = [
        {"label": "Compare", "intent": "compare"},
        {"label": "Unknown", "intent": "hack"},
    ]
    clean = sanitize_quick_actions(actions)
    assert all(a["intent"] != "hack" for a in clean)
    assert any(a["intent"] == "compare" for a in clean)


def test_validate_chat_request():
    good = {"message": "hi"}
    validate_chat_request(good)
    bad = {"payload": "not a dict"}
    try:
        validate_chat_request(bad)
        raise AssertionError("expected failure")
    except RequestValidationError:
        pass


def test_session_store_round_trip():
    store = InMemorySessionStore()
    sess = ChatSession()
    sess.last_intent = "plan"
    store.save(sess)
    loaded = store.load(sess.session_id)
    assert loaded and loaded.last_intent == "plan"
    # dict converters
    payload = session_to_dict(sess)
    restored = dict_to_session(payload)
    assert restored.session_id == sess.session_id


def test_session_store_clear():
    store = InMemorySessionStore()
    sess = ChatSession()
    store.save(sess)
    store.clear()
    assert store.load(sess.session_id) is None
