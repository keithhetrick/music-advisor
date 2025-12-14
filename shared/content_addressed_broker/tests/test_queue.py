import json
import time
from pathlib import Path

import hashlib

from content_addressed_broker.queue import EchoJobQueue


def _dummy_runner(*, features_path, out_root, track_id, run_id, config_hash, db_path, db_hash, probe_kwargs, **kwargs):
    cfg = config_hash or "cfg"
    src = "src123"
    out_dir = Path(out_root) / "echo" / cfg / src
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / "historical_echo.json"
    artifact.write_text(json.dumps({"track_id": track_id, "probe": probe_kwargs, "features": str(features_path)}))
    h = hashlib.sha256()
    h.update(artifact.read_bytes())
    sha = h.hexdigest()
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps({"artifact": {"sha256": sha, "etag": sha}}))
    return {"artifact": str(artifact), "manifest": str(manifest)}


def test_queue_writes_index_and_validates(tmp_path):
    out_root = tmp_path / "cas"
    queue = EchoJobQueue(_dummy_runner)
    job_id = queue.submit(
        features_path=str(tmp_path / "feat.json"),
        out_root=str(out_root),
        track_id="track-1",
        run_id="run-1",
        config_hash="cfg-1",
        db_path=None,
        db_hash=None,
        probe_kwargs={"k": "v"},
    )
    # wait for worker
    queue._q.join()  # type: ignore[attr-defined]
    job = queue.get(job_id)
    assert job and job["status"] == "done"
    result = job["result"]
    assert out_root.joinpath("echo/cfg-1/src123/manifest.json").is_file()
    assert out_root.joinpath("echo/index/track-1.json").is_file()
    idx = json.loads(out_root.joinpath("echo/index/track-1.json").read_text())
    assert idx["config_hash"] == "cfg-1"
    assert idx["source_hash"] == "src123"
    assert idx["artifact"].endswith("/historical_echo.json")
    assert idx["etag"] == result["etag"]


def test_queue_sets_error_on_validation_failure(tmp_path):
    def bad_runner(**kwargs):
        out_dir = Path(kwargs["out_root"]) / "echo" / "cfg" / "src"
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = out_dir / "historical_echo.json"
        artifact.write_text("{}")
        manifest = out_dir / "manifest.json"
        # Wrong hash on purpose
        manifest.write_text(json.dumps({"artifact": {"sha256": "deadbeef"}}))
        return {"artifact": str(artifact), "manifest": str(manifest)}

    queue = EchoJobQueue(bad_runner)
    job_id = queue.submit(
        features_path=str(tmp_path / "feat.json"),
        out_root=str(tmp_path / "cas"),
        track_id="track-err",
        run_id=None,
        config_hash="cfg",
        db_path=None,
        db_hash=None,
        probe_kwargs={},
    )
    queue._q.join()  # type: ignore[attr-defined]
    job = queue.get(job_id)
    assert job and job["status"] == "error"
    assert "validation_failed" in (job["error"] or "")
