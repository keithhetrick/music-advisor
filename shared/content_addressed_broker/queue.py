"""
In-process queue + pluggable runner for content-addressed artifact delivery.
"""
from __future__ import annotations

import importlib
import json
import sys
import threading
import logging
from queue import Queue
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from .utils import write_index_pointer, validate_artifact

RunnerFunc = Callable[..., Dict[str, Any]]


def load_runner(dotted_path: str) -> RunnerFunc:
    """Load a runner callable given a dotted path like module.sub:func."""
    if ":" not in dotted_path:
        raise ValueError("runner must be in form module.sub:callable")
    mod_name, func_name = dotted_path.split(":", 1)
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, func_name)
    if not callable(fn):
        raise TypeError(f"{dotted_path} is not callable")
    return fn


class EchoJobQueue:
    """Single-worker queue that invokes a pluggable runner and writes CAS/index pointers."""

    def __init__(
        self,
        runner: RunnerFunc,
        artifact_name: str = "historical_echo.json",
        manifest_name: str = "manifest.json",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._runner = runner
        self._artifact_name = artifact_name
        self._manifest_name = manifest_name
        self._log = logger or logging.getLogger(__name__)

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
        runner_kwargs: Optional[Dict[str, Any]] = None,
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
                "runner_kwargs": runner_kwargs or {},
            }
        )
        self._log.info(
            "submit job=%s features=%s track_id=%s config=%s",
            job_id,
            features_path,
            track_id,
            config_hash,
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
                self._log.info("start job=%s track_id=%s", job_id, job.get("track_id"))
                features_path = Path(job["features_path"]).expanduser()
                out_root = Path(job["out_root"]).expanduser()
                db_path = Path(job["db_path"]).expanduser() if job.get("db_path") else None

                # Invoke pluggable runner
                result = self._runner(
                    features_path=features_path,
                    out_root=out_root,
                    track_id=job["track_id"],
                    run_id=job["run_id"],
                    config_hash=job["config_hash"],
                    db_path=db_path,
                    db_hash=job["db_hash"],
                    probe_kwargs=job["probe_kwargs"],
                    **job.get("runner_kwargs", {}),
                )

                artifact_path = Path(result["artifact"])
                manifest_path = Path(result["manifest"])

                etag = None
                try:
                    ok, etag, _ = validate_artifact(artifact_path, manifest_path)
                    if not ok:
                        raise ValueError("hash_mismatch")
                except Exception as exc:  # noqa: BLE001
                    self._set_error(job_id, f"validation_failed: {exc}")
                    self._log.error("validation failed job=%s error=%s", job_id, exc)
                    continue

                if job.get("track_id") and etag:
                    cfg = manifest_path.parent.parent.name
                    src = manifest_path.parent.name
                    write_index_pointer(
                        out_root,
                        job["track_id"],
                        cfg,
                        src,
                        etag,
                        artifact_name=self._artifact_name,
                        manifest_name=self._manifest_name,
                    )
                self._set_result(
                    job_id,
                    {
                        "artifact_path": str(artifact_path),
                        "manifest_path": str(manifest_path),
                        "etag": etag,
                    },
                )
                self._log.info(
                    "done job=%s track_id=%s etag=%s artifact=%s",
                    job_id,
                    job.get("track_id"),
                    etag,
                    artifact_path,
                )
            except Exception as exc:  # noqa: BLE001
                self._set_error(job_id, str(exc))
                self._log.exception("error job=%s: %s", job_id, exc)
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
