"""
Minimal in-process job queue for Historical Echo runner.

This is intentionally lightweight (queue + worker thread) and opt-in. It wraps
the canonical runner so callers (e.g., TaskConductor HTTP layer) can enqueue
work without touching existing pipelines.
"""
from __future__ import annotations

import threading
import json
from queue import Queue
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4
import sys

HERE = Path(__file__).resolve()
REPO = HERE.parent.parent.parent  # repo root
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.hci.historical_echo_runner import run as run_echo
from tools.task_conductor.echo_utils import write_index_pointer


class EchoJobQueue:
    """Single-worker queue that runs Historical Echo jobs via the canonical runner."""

    def __init__(self) -> None:
        self._q: Queue[Dict[str, Any]] = Queue()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def submit(
        self,
        *,
        features_path: str,
        out_root: str,
        track_id: Optional[str],
        run_id: Optional[str],
        config_hash: Optional[str],
        db_path: Optional[str],
        db_hash: Optional[str],
        probe_kwargs: Dict[str, Any],
    ) -> str:
        job_id = str(uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "status": "pending",
                "error": None,
                "result": None,
            }
        self._q.put(
            {
                "job_id": job_id,
                "features_path": features_path,
                "out_root": out_root,
                "track_id": track_id,
                "run_id": run_id,
                "config_hash": config_hash,
                "db_path": db_path,
                "db_hash": db_hash,
                "probe_kwargs": probe_kwargs,
            }
        )
        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def _worker_loop(self) -> None:
        while True:
            job = self._q.get()
            job_id = job["job_id"]
            try:
                self._set_status(job_id, "running")
                features_path = Path(job["features_path"]).expanduser()
                out_root = Path(job["out_root"]).expanduser()
                db_path = Path(job["db_path"]).expanduser() if job.get("db_path") else None
                result = run_echo(
                    features_path=features_path,
                    out_root=out_root,
                    track_id=job["track_id"],
                    run_id=job["run_id"],
                    config_hash=job["config_hash"],
                    db_path=db_path,
                    db_hash=job["db_hash"],
                    probe_kwargs=job["probe_kwargs"],
                )
                artifact_path = result["artifact"]
                manifest_path = result["manifest"]
                etag = None
                try:
                    manifest = json.loads(Path(manifest_path).read_text())
                    etag = (manifest.get("artifact") or {}).get("etag")
                except Exception:
                    etag = None
                # Optional latest pointer by track_id
                if job.get("track_id") and etag:
                    write_index_pointer(
                        Path(job["out_root"]),
                        job["track_id"],
                        Path(manifest_path).parent.parent.name,
                        Path(manifest_path).parent.name,
                        etag,
                    )
                self._set_result(
                    job_id,
                    {
                        "artifact_path": str(artifact_path),
                        "manifest_path": str(manifest_path),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                self._set_error(job_id, str(exc))
            finally:
                self._q.task_done()

    def _set_status(self, job_id: str, status: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status

    def _set_result(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "done"
                self._jobs[job_id]["result"] = result

    def _set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "error"
                self._jobs[job_id]["error"] = error
