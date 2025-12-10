"""
Thin wrapper around the existing tools/chat backend.

Goal: single entrypoint for hosts (macOS app, CLI) while we migrate logic out of UI code.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from tools.chat.chat_router import route_message
from tools.chat.chat_context import ChatSession


@dataclass
class ChatRequest:
    prompt: str
    context_path: Optional[str] = None
    label: str = "No context"
    rate_limit_seconds: float = 0.0
    timeout_seconds: float = 0.0


@dataclass
class ChatResponse:
    reply: str
    label: str
    warning: Optional[str] = None
    rate_limited: bool = False
    timed_out: bool = False
    context_path: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "reply": self.reply,
                "label": self.label,
                "warning": self.warning,
                "rate_limited": self.rate_limited,
                "timed_out": self.timed_out,
                "context_path": self.context_path,
            }
        )


def _resolve_context(path: Optional[str]) -> Tuple[Optional[Path], Optional[str]]:
    if not path:
        return None, None
    p = Path(path)
    if not p.exists():
        return None, f"Context file missing: {p}"
    if not p.is_file():
        return None, f"Context is not a file: {p}"
    if not os.access(p, os.R_OK):
        return None, f"Context not readable: {p}"
    return p, None


def run(request: ChatRequest) -> ChatResponse:
    """
    Executes a chat request using the existing chat_router.
    Adds lightweight context validation and optional rate/timeout guards so hosts stay thin.
    """
    start = time.time()
    sess = ChatSession(session_id="engine")

    # Rate limit check
    if request.rate_limit_seconds > 0 and getattr(run, "_last_sent", None):
        delta = time.time() - run._last_sent  # type: ignore[attr-defined]
        if delta < request.rate_limit_seconds:
            return ChatResponse(
                reply="",
                label=request.label,
                warning="Rate limited; please wait",
                rate_limited=True,
                timed_out=False,
                context_path=request.context_path,
            )

    client_path, warn = _resolve_context(request.context_path)
    if warn:
        return ChatResponse(
            reply="",
            label=request.label,
            warning=warn,
            rate_limited=False,
            timed_out=False,
            context_path=request.context_path,
        )

    # Temporary offline placeholder: acknowledge prompt/context without dumping context or overlays.
    reply = _format_stub(prompt=request.prompt, client_path=client_path)

    elapsed = time.time() - start
    timed_out = request.timeout_seconds > 0 and elapsed > request.timeout_seconds
    run._last_sent = time.time()  # type: ignore[attr-defined]
    return ChatResponse(
        reply=str(reply),
        label=request.label,
        warning=warn,
        rate_limited=False,
        timed_out=timed_out,
        context_path=str(client_path) if client_path else None,
    )


def _format_stub(prompt: str, client_path: Optional[Path]) -> str:
    context_label = client_path.name if client_path else "none"
    return (
        f"Context: {context_label}\n"
        f"Prompt received. LLM not wired yet; no analysis performed."
    )
