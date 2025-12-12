import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import tools.task_conductor.echo_queue as eq


def test_queue_writes_index_pointer(monkeypatch):
    calls = {}

    def fake_run_echo(features_path, out_root, track_id, run_id, config_hash, db_path, db_hash, probe_kwargs):
        out_dir = Path(out_root) / "echo" / "cfg" / "src"
        out_dir.mkdir(parents=True, exist_ok=True)
        hist = out_dir / "historical_echo.json"
        hist.write_text(json.dumps({"ok": True}))
        manifest = out_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "artifact": {
                        "sha256": "deadbeef",
                        "etag": "deadbeef",
                        "path": "historical_echo.json",
                        "size": hist.stat().st_size,
                    }
                }
            )
        )
        return {
            "artifact": str(hist),
            "manifest": str(manifest),
        }

    def fake_write_index_pointer(out_root, track_id, cfg, src, etag):
        calls["out_root"] = str(out_root)
        calls["track_id"] = track_id
        calls["cfg"] = cfg
        calls["src"] = src
        calls["etag"] = etag
        idx = Path(out_root) / "echo" / "index"
        idx.mkdir(parents=True, exist_ok=True)
        (idx / f"{track_id}.json").write_text(
            json.dumps(
                {
                    "artifact": f"/echo/{cfg}/{src}/historical_echo.json",
                    "manifest": f"/echo/{cfg}/{src}/manifest.json",
                    "config_hash": cfg,
                    "source_hash": src,
                    "track_id": track_id,
                    "etag": etag,
                }
            )
        )

    monkeypatch.setattr(eq, "run_echo", fake_run_echo)
    monkeypatch.setattr(eq, "write_index_pointer", fake_write_index_pointer)

    with TemporaryDirectory() as tmp:
        q = eq.EchoJobQueue()
        feat = Path(tmp) / "song.features.json"
        feat.write_text("{}")
        job_id = q.submit(
            features_path=str(feat),
            out_root=tmp,
            track_id="track-123",
            run_id=None,
            config_hash="cfg",
            db_path=None,
            db_hash=None,
            probe_kwargs={},
        )
        # wait for worker to process
        deadline = time.time() + 5
        while time.time() < deadline:
            job = q.get(job_id)
            if job and job.get("status") == "done":
                break
            time.sleep(0.05)

        job = q.get(job_id)
        assert job is not None
        assert job["status"] == "done"
        assert calls.get("track_id") == "track-123"
        assert calls.get("cfg") == "cfg"
        assert calls.get("src") == "src"
        assert calls.get("etag") == "deadbeef"
        idx_path = Path(tmp) / "echo" / "index" / "track-123.json"
        assert idx_path.is_file()
        pointer = json.loads(idx_path.read_text())
        assert pointer["artifact"].endswith("/cfg/src/historical_echo.json")
        assert pointer["etag"] == "deadbeef"
