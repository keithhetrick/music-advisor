"""
Content-addressed broker: HTTP server + queue for immutable artifact delivery.
"""
from __future__ import annotations

import argparse
import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote

from .queue import EchoJobQueue, load_runner
from .utils import validate_artifact


class EchoHandler(BaseHTTPRequestHandler):
    """HTTP handler bound to a specific queue and CAS root."""

    queue: EchoJobQueue
    cas_root: Path
    artifact_name: str
    manifest_name: str

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
            runner_kwargs=data.get("runner_kwargs") or {},
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
            if fname == self.artifact_name:
                manifest_path = target.parent / self.manifest_name
                ok, etag, _ = validate_artifact(target, manifest_path) if manifest_path.is_file() else (False, None, {})
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
            elif fname == self.manifest_name:
                data = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.end_headers()
                self.wfile.write(data)
                return

        self._not_found()


def make_handler(queue: EchoJobQueue, cas_root: Path, artifact_name: str, manifest_name: str):
    """Bind queue and cas_root into a handler class."""

    class _Handler(EchoHandler):
        pass

    _Handler.queue = queue
    _Handler.cas_root = cas_root
    _Handler.artifact_name = artifact_name
    _Handler.manifest_name = manifest_name
    return _Handler


def serve(
    cas_root: Path,
    *,
    runner_path: str = "tools.hci.historical_echo_runner:run",
    host: str = "127.0.0.1",
    port: int = 8099,
    artifact_name: str = "historical_echo.json",
    manifest_name: str = "manifest.json",
) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    runner = load_runner(runner_path)
    queue = EchoJobQueue(runner, artifact_name=artifact_name, manifest_name=manifest_name)
    handler = make_handler(queue, cas_root, artifact_name, manifest_name)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"[content_addressed_broker] serving on http://{host}:{port} (cas_root={cas_root})")
    httpd.serve_forever()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Content-addressed broker (TaskConductor-style).")
    p.add_argument("--cas-root", default="data/echo_cas", help="CAS root directory")
    p.add_argument("--host", default="127.0.0.1", help="Listen host")
    p.add_argument("--port", type=int, default=8099, help="Listen port")
    p.add_argument("--runner", default="tools.hci.historical_echo_runner:run", help="Runner callable path (module:func)")
    p.add_argument("--artifact-name", default="historical_echo.json", help="Artifact filename")
    p.add_argument("--manifest-name", default="manifest.json", help="Manifest filename")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    serve(
        Path(args.cas_root),
        runner_path=args.runner,
        host=args.host,
        port=args.port,
        artifact_name=args.artifact_name,
        manifest_name=args.manifest_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
