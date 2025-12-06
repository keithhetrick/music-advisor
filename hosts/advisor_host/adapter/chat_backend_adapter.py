"""
Optional bridge to the modular chat backend in tools/chat.

This keeps the host thin: when enabled (HOST_CHAT_BACKEND_MODE != "off"),
we construct a backend ChatSession, point it at a client_rich.txt path,
and delegate routing to tools.chat.chat_router.route_message.
Gracefully no-op if the backend modules are unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from tools.chat.chat_context import ChatSession as BackendSession  # type: ignore
    from tools.chat.chat_router import route_message as backend_route_message  # type: ignore
except Exception:  # noqa: BLE001
    BackendSession = None
    backend_route_message = None

DEFAULT_MAXLEN = int(os.getenv("HOST_CHAT_BACKEND_MAXLEN", "400"))


def backend_enabled() -> bool:
    """
    Toggle via HOST_CHAT_BACKEND_MODE.
    Values: off | auto (default) | on
    """
    return os.getenv("HOST_CHAT_BACKEND_MODE", "auto").lower() != "off"


def configure_backend_session(
    host_session: Any, client_path: Optional[str] = None, max_length: Optional[int] = None
) -> Optional[Any]:
    """
    Ensure a backend ChatSession exists and (optionally) set the client path.
    """
    if not backend_enabled() or BackendSession is None:
        return None
    if not getattr(host_session, "backend_session", None):
        host_session.backend_session = BackendSession(
            session_id=host_session.session_id, max_length=max_length or DEFAULT_MAXLEN
        )
    backend = host_session.backend_session
    if client_path:
        try:
            backend.set_client_path(Path(client_path))
            host_session.backend_client_path = backend.client_path
        except Exception:
            pass
    return backend


def route_backend_message(
    host_session: Any, message: str, client_path: Optional[str] = None, tone: str = "neutral"
) -> Optional[Dict[str, Any]]:
    """
    Delegate a chat message to tools.chat if enabled and configured.
    Returns a host-shaped reply dict or None to signal fallback.
    """
    if not backend_enabled() or backend_route_message is None:
        return None
    backend = configure_backend_session(host_session, client_path=client_path, max_length=DEFAULT_MAXLEN)
    if backend is None or backend.client_path is None:
        return None
    reply_text = backend_route_message(backend, message, client_path=backend.client_path)
    return {"session_id": host_session.session_id, "reply": reply_text, "ui_hints": {"show_cards": [], "quick_actions": [], "tone": tone}}


__all__ = ["backend_enabled", "configure_backend_session", "route_backend_message"]
