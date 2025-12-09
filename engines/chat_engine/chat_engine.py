"""
Thin wrapper around the existing tools/chat backend.

Goal: single entrypoint for hosts (macOS app, CLI) while we migrate logic out of UI code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tools.chat.chat_router import route_message
from tools.chat.chat_context import ChatSession


@dataclass
class ChatRequest:
    prompt: str
    context_path: Optional[str] = None
    label: str = "No context"


@dataclass
class ChatResponse:
    reply: str
    label: str
    warning: Optional[str] = None
    rate_limited: bool = False
    timed_out: bool = False


def run(request: ChatRequest) -> ChatResponse:
    """
    Executes a chat request using the existing chat_router.
    """
    sess = ChatSession(session_id="engine")
    client_path: Optional[Path] = None
    if request.context_path:
        p = Path(request.context_path)
        if p.exists():
            client_path = p
    reply = route_message(sess, request.prompt, client_path=client_path)
    # route_message currently returns a string; rate-limit/timeout are not exposed.
    return ChatResponse(reply=str(reply), label=request.label)
