import http.client
import json
import threading
import time
from pathlib import Path

from content_addressed_broker.queue import EchoJobQueue
from content_addressed_broker.broker import make_handler


def _dummy_runner(*, features_path, out_root, track_id, run_id, config_hash, db_path, db_hash, probe_kwargs, **kwargs):
    cfg = config_hash or "cfg"
    src = "src123"
    out_dir = Path(out_root) / "echo" / cfg / src
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / "historical_echo.json"
    artifact.write_text(json.dumps({"track_id": track_id, "probe": probe_kwargs, "features": str(features_path)}))
    sha = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps({"artifact": {"sha256": sha, "etag": sha}}))
    return {"artifact": str(artifact), "manifest": str(manifest)}


def test_http_contract_submit_status_index_artifact(tmp_path):
    # Spin up broker on a random port
    queue = EchoJobQueue(_dummy_runner)
    handler = make_handler(queue, tmp_path, "historical_echo.json", "manifest.json")
    try:
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    except PermissionError:
        import pytest
        pytest.skip("port bind not permitted in this environment")
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        features = tmp_path / "feat.json"
        features.write_text("{}")

        # Submit job
        conn = http.client.HTTPConnection(host, port)
        payload = json.dumps({"features_path": str(features), "track_id": "foo"}).encode()
        conn.request("POST", "/echo/jobs", body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        assert resp.status == 202
        data = json.loads(resp.read())
        job_id = data["job_id"]

        # Poll until done
        for _ in range(20):
            conn.request("GET", f"/echo/jobs/{job_id}")
            r = conn.getresponse()
            assert r.status == 200
            status_payload = json.loads(r.read())
            if status_payload["status"] == "done":
                break
            time.sleep(0.05)
        else:
            raise AssertionError("job did not complete")

        # Fetch index (should exist)
        conn.request("GET", "/echo/index/foo.json")
        idx_resp = conn.getresponse()
        assert idx_resp.status == 200
        idx = json.loads(idx_resp.read())
        assert idx["track_id"] == "foo"

        # Fetch artifact with ETag caching
        conn.request("GET", idx["artifact"])
        art_resp = conn.getresponse()
        assert art_resp.status == 200
        etag = art_resp.getheader("ETag")
        body = art_resp.read()
        assert b"track_id" in body

        # If-None-Match
        conn.request("GET", idx["artifact"], headers={"If-None-Match": etag})
        notmod_resp = conn.getresponse()
        assert notmod_resp.status == 304
    finally:
        server.shutdown()
        server.server_close()
