import json
import threading
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from tools.task_conductor.echo_broker import make_handler
from http.server import ThreadingHTTPServer
import hashlib


class StubQueue:
    def __init__(self) -> None:
        self.jobs = {}

    def submit(
        self,
        *,
        features_path: str,
        out_root: str,
        track_id: str | None,
        run_id: str | None,
        config_hash: str | None,
        db_path: str | None,
        db_hash: str | None,
        probe_kwargs: dict,
    ) -> str:
        job_id = str(uuid4())
        self.jobs[job_id] = {"status": "pending", "error": None, "result": None}
        return job_id

    def get(self, job_id: str):
        return self.jobs.get(job_id)


@pytest.fixture()
def broker_server():
    with TemporaryDirectory() as tmp:
        cas_root = Path(tmp)
        queue = StubQueue()
        handler = make_handler(queue, cas_root)
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        except PermissionError:
            pytest.skip("Cannot bind HTTP server in this environment")
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield ("127.0.0.1", port, cas_root, queue)
        finally:
            httpd.shutdown()
            t.join()


def http_request(host, port, method, path, body=None, headers=None):
    conn = HTTPConnection(host, port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp, data


def test_post_jobs_and_job_status(broker_server, tmp_path):
    host, port, cas_root, queue = broker_server
    feat = tmp_path / "song.features.json"
    feat.write_text("{}")

    resp, data = http_request(
        host,
        port,
        "POST",
        "/echo/jobs",
        body=json.dumps({"features_path": str(feat), "track_id": "track-1"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status == 202
    job_id = json.loads(data)["job_id"]
    # Seed a fake result and mark done
    queue.jobs[job_id] = {"status": "done", "error": None, "result": {"artifact_path": "a", "manifest_path": "m"}}

    resp2, data2 = http_request(host, port, "GET", f"/echo/jobs/{job_id}")
    assert resp2.status == 200
    payload = json.loads(data2)
    assert payload["job_id"] == job_id
    assert payload["status"] == "done"


def test_index_decodes_encoded_track_id(broker_server):
    host, port, cas_root, _ = broker_server
    track_id = "Merry Christmas, Y'all - ai demo.mp3"
    idx_dir = cas_root / "echo" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    pointer = {
        "artifact": "/echo/cfg/src/historical_echo.json",
        "manifest": "/echo/cfg/src/manifest.json",
        "config_hash": "cfg",
        "source_hash": "src",
        "track_id": track_id,
        "etag": "etag123",
    }
    (idx_dir / f"{track_id}.json").write_text(json.dumps(pointer))

    encoded = "Merry%20Christmas,%20Y%27all%20-%20ai%20demo.mp3"
    resp, data = http_request(host, port, "GET", f"/echo/index/{encoded}.json")
    assert resp.status == 200
    payload = json.loads(data)
    assert payload["track_id"] == track_id


def test_historical_echo_serves_with_etag_and_304(broker_server, tmp_path):
    host, port, cas_root, _ = broker_server
    cfg = "cfg"
    src = "src"
    echo_dir = cas_root / "echo" / cfg / src
    echo_dir.mkdir(parents=True, exist_ok=True)
    # Write historical_echo and manifest with matching sha/etag
    hist_path = echo_dir / "historical_echo.json"
    hist_path.write_text(json.dumps({"hello": "world"}))
    sha = hashlib.sha256(hist_path.read_bytes()).hexdigest()
    manifest = {"artifact": {"sha256": sha, "etag": sha, "path": "historical_echo.json", "size": hist_path.stat().st_size}}
    (echo_dir / "manifest.json").write_text(json.dumps(manifest))

    resp, data = http_request(host, port, "GET", f"/echo/{cfg}/{src}/historical_echo.json")
    assert resp.status == 200
    assert resp.getheader("ETag") == sha
    assert json.loads(data) == {"hello": "world"}

    # Second request with If-None-Match should 304
    resp2, _ = http_request(
        host,
        port,
        "GET",
        f"/echo/{cfg}/{src}/historical_echo.json",
        headers={"If-None-Match": sha},
    )
    assert resp2.status == 304
