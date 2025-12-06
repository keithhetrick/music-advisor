"""
Chat/session layer (stateful, slice-aware).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from advisor_host.adapter import chat_backend_adapter, recommendation_adapter as rec_adapter
from advisor_host.host.formatters import format_slice
from advisor_host.intents.intents import detect_intent, sanitize_quick_actions
from advisor_host.logging.logger import log_event
from advisor_host.logging.metrics import record_metric, timing_ms
from advisor_host.schema.schema import validate_reply_shape
from advisor_host.tutorials.tutorials import get_tutorial, tutorial_list

PROFILES_PATH = Path(__file__).resolve().parents[1] / "config" / "host_profiles.yml"

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None


def load_profiles() -> Dict[str, Any]:
    if yaml is None or not PROFILES_PATH.exists():
        return {}
    return yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8")) or {}


HOST_PROFILES = load_profiles()


class ChatSession:
    def __init__(self, host_profile_id: str = "producer_advisor_v1"):
        self.session_id = str(uuid.uuid4())
        self.host_profile_id = host_profile_id
        self.last_recommendation: Optional[Dict[str, Any]] = None
        self.prev_recommendation: Optional[Dict[str, Any]] = None
        self.last_intent: Optional[str] = None
        self.offsets: Dict[str, int] = {}
        self.history: list[Dict[str, Any]] = []
        self.backend_session: Optional[Any] = None  # optional tools.chat session
        self.backend_client_path: Optional[Path] = None


def get_profile(host_profile_id: str) -> Dict[str, Any]:
    return HOST_PROFILES.get(host_profile_id) or HOST_PROFILES.get("default", {}) or {}


def handle_message(
    session: ChatSession,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
    market_norms_snapshot: Optional[Dict[str, Any]] = None,
    client_rich_path: Optional[str] = None,
) -> Dict[str, Any]:
    start_ts = time.time()
    correlation_id = str(uuid.uuid4())
    HISTORY_MAX = 50
    MAX_HISTORY_BYTES = int(os.getenv("HOST_MAX_HISTORY_BYTES", "65536"))
    MAX_REPLY_BYTES = int(os.getenv("HOST_MAX_REPLY_BYTES", "8192"))
    MAX_ADVISORY_BYTES = int(os.getenv("HOST_MAX_ADVISORY_BYTES", "131072"))
    PAGE_SIZE = int(os.getenv("HOST_PAGE_SIZE", "3"))
    profile = get_profile(session.host_profile_id)
    tone = profile.get("tone", "neutral")
    backend_mode = os.getenv("HOST_CHAT_BACKEND_MODE", "auto").lower()
    client_rich_path = client_rich_path or os.getenv("HOST_CHAT_CLIENT_PATH")
    if client_rich_path and backend_mode != "off" and session.backend_client_path is None:
        try:
            session.backend_client_path = Path(client_rich_path).expanduser()
            chat_backend_adapter.configure_backend_session(
                session, client_path=session.backend_client_path, max_length=MAX_REPLY_BYTES
            )
        except Exception:
            session.backend_client_path = None
    # If new payload provided, compute recommendation/advisory
    if payload is not None:
        session.prev_recommendation = session.last_recommendation
        if market_norms_snapshot:
            session.last_recommendation = rec_adapter.run(payload, market_norms_snapshot)
            meta = {
                "region": market_norms_snapshot.get("region"),
                "tier": market_norms_snapshot.get("tier"),
                "version": market_norms_snapshot.get("version"),
            }
            meta_str = ", ".join([f"{k}={v}" for k, v in meta.items() if v])
            norms_note = f" Using market norms: {meta_str}."
        else:
            session.last_recommendation = rec_adapter.run_without_norms(payload)
            norms_note = " Note: no market_norms snapshot provided; using advisory-only path."
        session.last_intent = None
        session.offsets.clear()
        # Optional: configure chat backend context if enabled and path available
        inferred_path: Optional[str]
        try:
            inferred_path = client_rich_path or payload.get("client_rich_path") or payload.get("client_rich")  # type: ignore[arg-type]
        except Exception:
            inferred_path = client_rich_path
        if inferred_path and backend_mode != "off":
            chat_backend_adapter.configure_backend_session(
                session, client_path=inferred_path, max_length=MAX_REPLY_BYTES
            )
        session.history.append({"role": "user", "content": message})
        session.history.append({"role": "assistant", "content": "analysis_generated"})
        intro = {
            "session_id": session.session_id,
            "reply": (
                "Received audio payload and generated an analysis. Ask about tempo, groove, "
                "loudness, mood, or improvements."
            )
            + norms_note,
            "ui_hints": {
                "show_cards": ["hci", "axes", "optimization", "historical_echo"],
                "quick_actions": [],
                "tone": tone,
                "primary_slices": profile.get("primary_slices", []),
            },
        }
        return intro

    if session.last_recommendation is None:
        log_event("handle_message", {"session_id": session.session_id, "status": "no_analysis"})
        if session.last_intent:
            resolved_intent = session.last_intent
        else:
            resolved_intent = detect_intent(message)
            session.last_intent = resolved_intent

        if resolved_intent in ("tutorial", "capabilities", "general", "summarize", "expand", "health"):
            reply_text = (
                "I analyze precomputed /audio payloads (features_full + audio_axes + HCI). "
                "Send a .client.json/.client.rich.txt payload to begin. "
                "Optional: include a market_norms snapshot for norm-aware advice. "
                "Intents: structure/groove/loudness/mood/historical/optimize/plan/compare/health, "
                "plus 'help' or 'tutorial' for guidance. "
                "Quick start: POST /chat with message='analyze' and your payload."
            )
        else:
            reply_text = "No analysis yet. Provide an /audio payload to begin (features_full + audio_axes + HCI)."
        ui_hints = {
            "show_cards": [],
            "quick_actions": [
                {"label": "Getting started", "intent": "tutorial"},
                {"label": "Commands", "intent": "commands"},
            ],
            "tone": tone,
            "primary_slices": profile.get("primary_slices", []),
        }
        return {"session_id": session.session_id, "reply": reply_text, "ui_hints": ui_hints}

    lower_msg = message.lower()
    if "more" in lower_msg and session.last_intent:
        intent = session.last_intent
        session.offsets[intent] = session.offsets.get(intent, 0) + PAGE_SIZE
    else:
        intent = detect_intent(message)
        session.last_intent = intent
        session.offsets[intent] = 0
    if intent == "status":
        intent = "health"

    rec = dict(session.last_recommendation)
    # inject prev rec for compare
    if intent == "compare" and session.prev_recommendation:
        rec["_prev_recommendation"] = session.prev_recommendation

    # Optional: delegate to tools.chat backend when configured and a client path is known
    if backend_mode != "off":
        backend_reply = chat_backend_adapter.route_backend_message(
            session,
            message,
            client_path=session.backend_client_path,
            tone=tone,
        )
        if backend_reply:
            return backend_reply

    if intent == "tutorial":
        tut = get_tutorial(message.strip().lower()) if message else get_tutorial("getting_started")
        if not tut:
            tlist = tutorial_list()
            reply_text = "Available tutorials:\n" + "\n".join([f"- {t['id']}: {t['title']}" for t in tlist])
            ui_hints = {
                "show_cards": [],
                "quick_actions": [{"label": "Show getting started", "intent": "tutorial"}],
                "tone": tone,
                "primary_slices": profile.get("primary_slices", []),
            }
        else:
            parts = [tut.get("title", "Tutorial")]
            parts.extend(tut.get("steps", []))
            tips = tut.get("tips") or []
            if tips:
                parts.append("Tips:")
                parts.extend(tips)
            reply_text = "\n".join(parts)
            ui_hints = {
                "show_cards": [],
                "quick_actions": [{"label": "List tutorials", "intent": "tutorial"}],
                "tone": tone,
                "primary_slices": profile.get("primary_slices", []),
            }
    else:
        reply_text, ui_hints = format_slice(intent, rec, profile, tone, session.offsets)

    formatted: Dict[str, Any] = {"session_id": session.session_id, "reply": reply_text, "ui_hints": ui_hints}

    # Dynamic quick actions based on availability
    qa = ui_hints.get("quick_actions", []).copy()
    if session.prev_recommendation:
        qa.append({"label": "Compare to previous", "intent": "compare"})
    if rec.get("advisor_sections"):
        qa.append({"label": "Show plan", "intent": "plan"})
    qa.append({"label": "Show status", "intent": "health"})
    formatted["ui_hints"]["quick_actions"] = sanitize_quick_actions(qa)

    log_event(
        "handle_message",
        {
            "session_id": session.session_id,
            "correlation_id": correlation_id,
            "intent": intent,
            "tone": tone,
            "norms_present": bool(rec.get("market_norms_used")),
            "advisor_mode": rec.get("advisor_mode"),
            "rec_version": rec.get("rec_version"),
            "reply_len": len(reply_text),
            "_more": ui_hints.get("_more"),
        },
    )
    record_metric(
        "chat.handle_message.latency_ms",
        labels={"intent": intent, "norms": bool(rec.get("market_norms_used")), "correlation_id": correlation_id},
        value=timing_ms(start_ts),
    )

    session.history.append({"role": "user", "content": message})
    session.history.append({"role": "assistant", "content": reply_text})
    # Trim history to avoid unbounded growth
    if len(session.history) > HISTORY_MAX:
        session.history = session.history[-HISTORY_MAX:]

    # Enforce history byte budget
    def _history_size_bytes() -> int:
        try:
            return len(json.dumps(session.history))
        except Exception:
            return 0

    while _history_size_bytes() > MAX_HISTORY_BYTES and len(session.history) > 1:
        session.history = session.history[2:]

    # Enforce advisory size budget
    try:
        if session.last_recommendation and len(json.dumps(session.last_recommendation)) > MAX_ADVISORY_BYTES:
            session.last_recommendation = None
            formatted["ui_hints"].setdefault("warnings", []).append(
                "Analysis too large to retain in session; rerun with smaller payload."
            )
    except Exception:
        pass

    # Enforce reply size cap
    try:
        if len(formatted["reply"].encode("utf-8")) > MAX_REPLY_BYTES:
            truncated = formatted["reply"].encode("utf-8")[:MAX_REPLY_BYTES].decode("utf-8", errors="ignore")
            formatted["reply"] = truncated + " …"
            formatted["ui_hints"].setdefault("warnings", []).append("Reply truncated for size.")
    except Exception:
        pass

    # Signal when no more content available for paging
    if intent == session.last_intent and ui_hints.get("_more") is False:
        formatted["ui_hints"].setdefault("warnings", []).append("No more content to show for this topic.")
    # Norms warning if absent
    if not rec.get("market_norms_used"):
        formatted["ui_hints"].setdefault("warnings", []).append(
            "No market_norms snapshot provided; using advisory-only path."
        )
    else:
        norms = rec.get("market_norms_used") or {}
        ts = norms.get("last_refreshed_at")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else None
            max_age_days = int(os.getenv("HOST_NORMS_STALE_DAYS", "90"))
            if dt and (datetime.now(timezone.utc) - dt).days > max_age_days:
                formatted["ui_hints"].setdefault("warnings", []).append("Norms snapshot may be stale.")
        except Exception:
            pass
    # If missing key fields, add remediation quick-actions
    missing_fields = []
    if not rec.get("axes"):
        missing_fields.append("audio_axes")
    if rec.get("canonical_hci") is None:
        missing_fields.append("HCI score")
    if missing_fields:
        formatted["ui_hints"].setdefault("warnings", []).append(
            f"Missing fields: {', '.join(missing_fields)}. Re-run feature pack to include them."
        )
        formatted["ui_hints"].setdefault("quick_actions", []).append(
            {"label": "How to include fields", "intent": "tutorial"}
        )

    # Ensure outbound shape
    validate_reply_shape(formatted)

    return formatted
