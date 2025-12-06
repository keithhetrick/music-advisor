#!/usr/bin/env python3
"""
Minimal HTTP stub exposing the chat handler.

Run:
  HOST_LOG_PATH=logs/host.jsonl python -m advisor_host.cli.http_stub

Endpoints:
  POST /chat
    {
      "message": "...",
      "payload": {...optional /audio payload...},
      "norms": {...optional snapshot...},
      "profile": "producer_advisor_v1",
      "session": {...optional session JSON from previous call...}
    }
    Returns: chat reply + session snapshot
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from advisor_host.auth.auth import AuthError
from advisor_host.auth.providers import GoogleAuthProvider, NoAuthProvider, StaticBearerAuthProvider
from advisor_host.host.chat import ChatSession, handle_message
from advisor_host.host.request_validation import RequestValidationError, enforce_size_caps, validate_chat_request
from advisor_host.logging.metrics import record_metric, timing_ms
from advisor_host.session.session_store import (
    FileSessionStore,
    InMemorySessionStore,
    RedisSessionStore,
    dict_to_session,
    session_to_dict,
)


def _kill_port_listeners(port: int) -> None:
    """
    Best-effort helper: terminate any process listening on the given port.
    Uses lsof/kill (Unix/macOS); noop if unavailable.
    """
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
        pids = [pid.strip() for pid in out.splitlines() if pid.strip()]
        for pid in pids:
            # SIGTERM first, SIGKILL fallback
            subprocess.run(["kill", pid], check=False)
            subprocess.run(["kill", "-9", pid], check=False)
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    store: Any = InMemorySessionStore()
    rate_window_secs = int(os.getenv("HOST_RATE_WINDOW_SECS", "60"))
    rate_limit = int(os.getenv("HOST_RATE_LIMIT", "120"))  # requests per IP per window
    ip_hits: Dict[str, list[float]] = {}
    max_body_bytes = int(os.getenv("HOST_MAX_BODY_BYTES", "100000"))
    auth_token = os.getenv("HOST_AUTH_TOKEN")
    google_client_id = os.getenv("HOST_GOOGLE_CLIENT_ID")
    max_payload_bytes = int(os.getenv("HOST_MAX_PAYLOAD_BYTES", "262144"))  # 256KB
    max_norms_bytes = int(os.getenv("HOST_MAX_NORMS_BYTES", "262144"))  # 256KB
    admin_token = os.getenv("HOST_ADMIN_TOKEN")
    cors_allow_origin = os.getenv("HOST_CORS_ALLOW_ORIGIN")

    def _add_cors_headers(self):
        if self.cors_allow_origin:
            self.send_header("Access-Control-Allow-Origin", self.cors_allow_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status: int, payload: dict, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(204)
        self._add_cors_headers()
        self.end_headers()
        return

    def do_GET(self):
        if self.path == "/":
            accept = self.headers.get("Accept", "")
            payload = {
                "status": "ok",
                "message": "advisor_host chat stub. POST /chat with {message,payload?,norms?,session?}.",
                "endpoints": {
                    "/chat": "POST chat messages",
                    "/health": "GET health/status",
                    "/admin/clear": "GET clear sessions (optional bearer admin token)",
                },
            }
            if "text/html" in accept:
                html = """
                <html><body>
                <h3>advisor_host chat stub</h3>
                <form method="POST" action="/chat">
                  <label>Message</label><br/>
                  <input name="message" value="what is this app?" size="60"/><br/><br/>
                  <label>Payload (JSON)</label><br/>
                  <textarea name="payload" rows="8" cols="80">{}</textarea><br/><br/>
                  <label>Session (optional JSON)</label><br/>
                  <textarea name="session" rows="4" cols="80"></textarea><br/><br/>
                  <label>Norms (optional JSON)</label><br/>
                  <textarea name="norms" rows="4" cols="80"></textarea><br/><br/>
                  <button type="submit">Send</button>
                </form>
                <p>Or POST JSON directly to /chat.</p>
                </body></html>
                """.format(
                    json.dumps({"message": "analyze", "payload": {}}, indent=2)
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())
            else:
                self._send_json(200, payload)
            return
        if self.path == "/health":
            store_status = "ok"
            try:
                from advisor_host.session.session_store import RedisSessionStore  # type: ignore

                if isinstance(self.store, RedisSessionStore):
                    self.store._redis.ping()  # type: ignore[attr-defined]
            except Exception:
                store_status = "degraded"
            self._send_json(
                200,
                {
                    "status": "ok",
                    "message": "advisor_host stub running",
                    "store": self.store.__class__.__name__,
                    "store_status": store_status,
                    "uptime": time.time() - getattr(self.server, "start_ts", time.time()),
                },
            )
            return
        if self.path == "/admin/clear":
            if self.admin_token:
                hdr = self.headers.get("Authorization", "")
                if hdr != f"Bearer {self.admin_token}":
                    self._send_json(401, {"error": "unauthorized"})
                    return
            self.store.clear()
            self.ip_hits.clear()
            self._send_json(200, {"status": "cleared"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > self.max_body_bytes:
            self._send_json(413, {"error": "request too large"})
            return

        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode())
            validate_chat_request(data)
            enforce_size_caps(data, self.max_payload_bytes, self.max_norms_bytes)
        except RequestValidationError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except Exception:
            self._send_json(400, {"error": "invalid JSON or request"})
            return

        # Optional auth: Google ID token or static bearer
        # Auth provider selection
        provider: Any
        if self.google_client_id:
            verify_sig = os.getenv("HOST_VERIFY_GOOGLE_SIG", "").lower() in ("1", "true", "yes")
            provider = GoogleAuthProvider(self.google_client_id, verify_sig=verify_sig)
        elif self.auth_token:
            provider = StaticBearerAuthProvider(self.auth_token)
        else:
            provider = NoAuthProvider()

        user_id = None
        try:
            ctx = provider.verify({k: self.headers.get(k, "") for k in self.headers.keys()})
            user_id = ctx.user_id
        except AuthError as exc:
            if not isinstance(provider, NoAuthProvider):
                self._send_json(401, {"error": str(exc)})
                return

        # Simple per-user/IP rate limiting
        ip = self.client_address[0] if self.client_address else "unknown"
        rate_key = user_id or ip
        now = time.time()
        hits = self.ip_hits.get(rate_key, [])
        hits = [h for h in hits if now - h < self.rate_window_secs]
        if len(hits) >= self.rate_limit:
            record_metric("http_stub.rate_limit", labels={"ip": ip, "user": user_id or "anon"})
            self._send_json(429, {"error": "rate limit exceeded"})
            return
        hits.append(now)
        self.ip_hits[rate_key] = hits

        req_start = now
        # session handling
        incoming_session = data.get("session")
        session_id = incoming_session.get("session_id") if isinstance(incoming_session, dict) else None
        sess = None
        if session_id:
            sess = self.store.load(session_id)
        if sess is None:
            sess = ChatSession(host_profile_id=data.get("profile", "producer_advisor_v1"))
        elif incoming_session:
            # allow full snapshot restoration
            try:
                sess = dict_to_session(incoming_session)
            except Exception:
                pass

        resp = handle_message(
            sess,
            data.get("message", ""),
            payload=data.get("payload"),
            market_norms_snapshot=data.get("norms"),
            client_rich_path=data.get("client_rich_path"),
        )
        # persist session
        self.store.save(sess)
        session_snapshot: Dict[str, Any] = session_to_dict(sess)
        resp_out = {"reply": resp, "session": session_snapshot, "user": user_id}
        record_metric(
            "http_stub.request",
            labels={"path": "/chat", "user": user_id or "anon"},
            value=timing_ms(req_start),
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp_out).encode())


def run(server_class=HTTPServer, handler_class=Handler, port: int | None = None, force_port: bool = False):
    actual_port = port or int(os.getenv("HOST_PORT", "8080"))
    if force_port or os.getenv("HOST_FORCE_PORT", "").lower() in ("1", "true", "yes"):
        _kill_port_listeners(actual_port)

    # Session store selection
    store_kind = os.getenv("HOST_SESSION_STORE", "memory").lower()
    if store_kind == "redis":
        Handler.store = RedisSessionStore(os.getenv("REDIS_URL"))
    elif store_kind == "file":
        from pathlib import Path

        root_default = os.getenv("HOST_SESSION_DIR")
        if root_default:
            root = Path(root_default)
        else:
            from ma_config.paths import get_data_root
            root = get_data_root() / "sessions"
        Handler.store = FileSessionStore(root)
    else:
        Handler.store = InMemorySessionStore()

    server_address = ("", actual_port)
    try:
        httpd = server_class(server_address, handler_class)
    except OSError as exc:
        # If the port is busy and force flag is set, try a one-time kill+retry.
        force_env = os.getenv("HOST_FORCE_PORT", "").lower() in ("1", "true", "yes")
        if getattr(exc, "errno", None) == 48 and (force_port or force_env):
            _kill_port_listeners(actual_port)
            httpd = server_class(server_address, handler_class)
        else:
            raise
    httpd.start_ts = time.time()
    print(f"Serving advisor_host HTTP stub on port {actual_port}")
    httpd.serve_forever()


if __name__ == "__main__":
    env_port = int(os.getenv("HOST_PORT", "8080"))
    env_force = os.getenv("HOST_FORCE_PORT", "").lower() in ("1", "true", "yes")
    run(port=env_port, force_port=env_force)
