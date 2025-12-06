from pathlib import Path

from advisor_host.adapter import chat_backend_adapter
from advisor_host.host.chat import ChatSession


class _DummyBackendSession:
    def __init__(self, session_id: str, max_length: int | None = None):
        self.session_id = session_id
        self.max_length = max_length
        self.client_path: Path | None = None

    def set_client_path(self, path: Path) -> None:
        self.client_path = Path(path)


def test_backend_disabled_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("HOST_CHAT_BACKEND_MODE", "off")
    session = ChatSession()
    client_path = tmp_path / "song.client.rich.txt"
    client_path.write_text("# dummy")
    resp = chat_backend_adapter.route_backend_message(session, "hi", client_path=str(client_path))
    assert resp is None


def test_backend_route_when_enabled(monkeypatch, tmp_path):
    called: list[tuple] = []

    def fake_route(sess, msg, client_path=None):
        called.append((sess, msg, client_path))
        return "ok"

    monkeypatch.setenv("HOST_CHAT_BACKEND_MODE", "on")
    monkeypatch.setattr(chat_backend_adapter, "BackendSession", _DummyBackendSession)
    monkeypatch.setattr(chat_backend_adapter, "backend_route_message", fake_route)

    session = ChatSession()
    client_path = tmp_path / "song.client.rich.txt"
    client_path.write_text("# dummy")

    chat_backend_adapter.configure_backend_session(session, client_path=str(client_path), max_length=123)
    resp = chat_backend_adapter.route_backend_message(session, "hello", client_path=str(client_path), tone="neutral")

    assert resp is not None
    assert resp["reply"] == "ok"
    assert called
    assert isinstance(session.backend_session, _DummyBackendSession)
    assert session.backend_session.client_path == client_path
