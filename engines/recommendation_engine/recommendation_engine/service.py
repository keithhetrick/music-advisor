"""
Minimal HTTP service wrapper for the recommendation engine.
Optional: use with REC_ENGINE_MODE=remote in the adapter.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from recommendation_engine.engine.recommendation import compute_recommendation


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        if self.path != "/recommendation":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode())
            payload = data.get("payload") or {}
            norms = data.get("norms") or {}
            resp = compute_recommendation(payload, norms)
            self._send(200, resp)
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"error": str(exc)})


def run():
    port = int(os.getenv("REC_ENGINE_PORT", "8100"))
    server_address = ("", port)
    httpd = HTTPServer(server_address, Handler)
    print(f"Recommendation engine service on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
