"""
TaskConductor-style broker + queue for Historical Echo (opt-in).

Endpoints (when run as a standalone HTTP service):
  POST /echo/jobs           -> submit job (features_path + probe params)
  GET  /echo/jobs/{job_id}  -> job status + artifact pointers if done
  GET  /echo/{cfg}/{src}/historical_echo.json -> serve artifact with ETag
  GET  /echo/{cfg}/{src}/manifest.json        -> serve manifest
  GET  /echo/index/{track_id}.json            -> "latest" pointer (optional)

This is intentionally lightweight: stdlib HTTP server, single-worker queue,
no new dependencies. Existing flows are untouched; enable only when desired.
"""
from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

import sys
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve()
REPO = HERE.parent.parent.parent  # repo root
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.task_conductor.echo_queue import EchoJobQueue
from tools.task_conductor.echo_utils import validate_artifact


class EchoHandler(BaseHTTPRequestHandler):
    """HTTP handler bound to a specific queue and CAS root."""

    queue: EchoJobQueue
    cas_root: Path

    def _send_json(self, status: int, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/echo/jobs":
            self._not_found()
            return
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
        except Exception:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        features_path = data.get("features_path")
        if not features_path or not Path(features_path).expanduser().is_file():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "features_path_missing"})
            return

        probe_kwargs = data.get("probe") or {}
        job_id = self.queue.submit(
            features_path=str(Path(features_path).expanduser()),
            out_root=str(self.cas_root),
            track_id=data.get("track_id"),
            run_id=data.get("run_id"),
            config_hash=data.get("config_hash"),
            db_path=data.get("db_path"),
            db_hash=data.get("db_hash"),
            probe_kwargs=probe_kwargs,
        )
        self._send_json(HTTPStatus.ACCEPTED, {"job_id": job_id, "status": "pending"})

    def do_GET(self) -> None:  # noqa: N802
        # Job status
        if self.path.startswith("/echo/jobs/"):
            job_id = self.path.split("/")[3] if len(self.path.split("/")) >= 4 else ""
            job = self.queue.get(job_id)
            if not job:
                self._not_found()
                return
            self._send_json(HTTPStatus.OK, {"job_id": job_id, **job})
            return

        # Index pointer
        if self.path.startswith("/echo/index/"):
            track_id = unquote(self.path.split("/")[-1])
            idx_path = self.cas_root / "echo" / "index" / track_id
            if not idx_path.is_file():
                self._not_found()
                return
            payload = json.loads(idx_path.read_text())
            self._send_json(HTTPStatus.OK, payload, headers={"Cache-Control": "max-age=60"})
            return

        # Artifact/manifest serving
        parts = [p for p in self.path.split("/") if p]
        if len(parts) >= 4 and parts[0] == "echo":
            cfg, src, fname = parts[1], parts[2], parts[3]
            target = self.cas_root / "echo" / cfg / src / fname
            if not target.is_file():
                self._not_found()
                return
            if fname == "historical_echo.json":
                manifest_path = target.parent / "manifest.json"
                ok, etag, manifest = validate_artifact(target, manifest_path) if manifest_path.is_file() else (False, None, {})
                if not ok:
                    self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "hash_mismatch"})
                    return
                inm = self.headers.get("If-None-Match")
                if etag and inm == etag:
                    self.send_response(HTTPStatus.NOT_MODIFIED)
                    self.send_header("ETag", etag)
                    self.end_headers()
                    return
                data = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                if etag:
                    self.send_header("ETag", etag)
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.end_headers()
                self.wfile.write(data)
                return
            elif fname == "manifest.json":
                data = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.end_headers()
                self.wfile.write(data)
                return

        self._not_found()


def make_handler(queue: EchoJobQueue, cas_root: Path):
    """Bind queue and cas_root into a handler class."""

    class _Handler(EchoHandler):
        pass

    _Handler.queue = queue
    _Handler.cas_root = cas_root
    return _Handler


def serve(cas_root: Path, host: str = "127.0.0.1", port: int = 8099) -> None:
    queue = EchoJobQueue()
    handler = make_handler(queue, cas_root)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"[echo_broker] serving on http://{host}:{port} (cas_root={cas_root})")
    httpd.serve_forever()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TaskConductor-style Historical Echo broker (opt-in).")
    p.add_argument("--cas-root", default=os.environ.get("MA_ECHO_CAS_ROOT", "data/echo_cas"), help="CAS root")
    p.add_argument("--host", default="127.0.0.1", help="Listen host (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8099, help="Listen port (default 8099)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    serve(Path(args.cas_root), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
