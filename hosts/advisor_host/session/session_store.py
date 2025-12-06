"""
Lightweight, pluggable session persistence for advisor_host chat.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, cast

if TYPE_CHECKING:
    from advisor_host.host.chat import ChatSession  # pragma: no cover


def session_to_dict(session: "ChatSession") -> Dict:
    return {
        "session_id": session.session_id,
        "host_profile_id": session.host_profile_id,
        "last_recommendation": session.last_recommendation,
        "prev_recommendation": session.prev_recommendation,
        "last_intent": session.last_intent,
        "offsets": session.offsets,
        "history": session.history,
        "backend_client_path": str(session.backend_client_path) if getattr(session, "backend_client_path", None) else None,
    }


def dict_to_session(data: Dict) -> "ChatSession":
    from advisor_host.host.chat import ChatSession  # local import to avoid circular

    sess = ChatSession(host_profile_id=data.get("host_profile_id", "producer_advisor_v1"))
    sess.session_id = data.get("session_id", sess.session_id)
    sess.last_recommendation = data.get("last_recommendation")
    sess.prev_recommendation = data.get("prev_recommendation")
    sess.last_intent = data.get("last_intent")
    sess.offsets = data.get("offsets") or {}
    sess.history = data.get("history") or []
    backend_path = data.get("backend_client_path")
    if backend_path:
        try:
            sess.backend_client_path = Path(backend_path).expanduser()
        except Exception:
            sess.backend_client_path = None
    return sess


class SessionStore(Protocol):
    def save(self, session: "ChatSession") -> None: ...

    def load(self, session_id: str) -> "ChatSession" | None: ...

    def clear(self) -> None: ...


class InMemorySessionStore:
    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def save(self, session: ChatSession) -> None:
        self._store[session.session_id] = session_to_dict(session)

    def load(self, session_id: str) -> ChatSession | None:
        data = self._store.get(session_id)
        return dict_to_session(data) if data else None

    def clear(self) -> None:
        self._store.clear()


class FileSessionStore:
    """
    Stores sessions as JSON files under a root directory.
    """

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def save(self, session: ChatSession) -> None:
        path = self._path(session.session_id)
        path.write_text(json.dumps(session_to_dict(session)), encoding="utf-8")

    def load(self, session_id: str) -> ChatSession | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict_to_session(data)

    def clear(self) -> None:
        if self.root.exists():
            for p in self.root.glob("*.json"):
                try:
                    p.unlink()
                except Exception:
                    continue


class RedisSessionStore:
    """
    Optional Redis-backed store. Requires `redis` package and REDIS_URL env.
    """

    def __init__(self, url: Optional[str] = None, prefix: str = "advisor_host:session"):
        self.url = url or os.getenv("REDIS_URL")
        if not self.url:
            raise RuntimeError("RedisSessionStore requires REDIS_URL or url param")
        try:
            import redis  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("RedisSessionStore requires `redis` package") from exc
        self._redis = redis.Redis.from_url(self.url)
        self.prefix = prefix

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}:{session_id}"

    def save(self, session: ChatSession) -> None:
        self._redis.set(self._key(session.session_id), json.dumps(session_to_dict(session)))

    def load(self, session_id: str) -> ChatSession | None:
        raw = cast(Any, self._redis.get(self._key(session_id)))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(cast(str, raw))
        return dict_to_session(data)

    def clear(self) -> None:
        try:
            keys = list(cast(Any, self._redis.keys(f"{self.prefix}:*")))
            if keys:
                self._redis.delete(*keys)  # type: ignore[arg-type]
        except Exception:
            pass


# Backwards-compatible helpers for CLI usage
def save_session(session: ChatSession, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session_to_dict(session)), encoding="utf-8")


def load_session(path: Path) -> ChatSession:
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict_to_session(data)


__all__ = [
    "SessionStore",
    "InMemorySessionStore",
    "FileSessionStore",
    "RedisSessionStore",
    "session_to_dict",
    "dict_to_session",
    "save_session",
    "load_session",
]
