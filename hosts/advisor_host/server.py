#!/usr/bin/env python3
"""
Minimal FastAPI shim exposing /chat.

Starts a simple host that accepts:
- message (str)
- optional audio_payload (JSON)
- optional norms_path (overrides default)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from advisor_host.config import default_norms_path
from advisor_host.host.chat import ChatSession, handle_message

app = FastAPI(title="advisor_host", version="0.0.1")

sessions: Dict[str, ChatSession] = {}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    host_profile_id: Optional[str] = "producer_advisor_v1"
    message: str
    audio_payload: Optional[Dict[str, Any]] = None
    norms_path: Optional[str] = None
    client_rich_path: Optional[str] = None


def load_norms(norms_path: Optional[str]) -> Optional[Dict[str, Any]]:
    path = Path(norms_path) if norms_path else default_norms_path()
    if path and path.exists():
        return json.loads(path.read_text())
    return None


@app.post("/chat")
def chat(req: ChatRequest):
    session = sessions.get(req.session_id or "")
    if session is None:
        session = ChatSession(host_profile_id=req.host_profile_id or "producer_advisor_v1")
        sessions[session.session_id] = session
    norms = load_norms(req.norms_path)
    resp = handle_message(
        session,
        req.message,
        payload=req.audio_payload,
        market_norms_snapshot=norms,
        client_rich_path=req.client_rich_path,
    )
    return resp


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("advisor_host.server:app", host="0.0.0.0", port=8080, reload=False)
