from advisor_host.host.chat import ChatSession, handle_message
from recommendation_engine.tests.fixtures import sample_market_norms, sample_payload


def test_load_loop_history_cap():
    session = ChatSession()
    handle_message(session, "analyze", payload=sample_payload, market_norms_snapshot=sample_market_norms)
    for i in range(200):
        handle_message(session, f"groove {i}")
    assert len(session.history) <= 50
