"""
Lightweight chat session context holder.
Keeps per-session defaults like last client rich path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ChatSession:
    session_id: str
    client_path: Optional[Path] = None
    detail: str = "summary"
    max_length: int = 400
    last_intent: Optional[str] = None
    last_reply: Optional[str] = None
    history: list = field(default_factory=list)
    cache: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)  # optional: paraphrase_fn, intent_model

    def set_client_path(self, path: Path) -> None:
        self.client_path = path.expanduser().resolve()


__all__ = ["ChatSession"]
