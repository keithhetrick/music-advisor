"""Parallel/serial project execution helpers."""
from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Dict, List, Tuple

from .cache import hash_project, should_skip_cached, update_cache, write_artifact
from .env import LAST_RESULTS_FILE


def _print_summary(results, title: str = "Summary") -> None:
    print(title)
    for entry in results:
        cached = " (cached)" if entry.get("cached") else ""
        print(f"- {entry.get('project')}: rc={entry.get('rc')} duration={entry.get('duration'):.1f}s{cached}")


def record_results(results: List[Dict[str, object]], label: str, *, last_results_file=LAST_RESULTS_FILE) -> None:
    if not last_results_file:
        return
    payload = {"label": label, "results": results, "ts": time.time()}
    try:
        last_results_file.write_text(json.dumps(payload, indent=2))
    except Exception:
        pass


def run_projects_parallel(orch, projects, names, max_workers: int, cache_mode: str = "off", retries: int = 0, progress_cb=None):
    results = []
    failures = []

    def _run(name: str):
        project = projects[name]
        skip, info = should_skip_cached(project, "test", cache_mode)
        if skip:
            return name, 0, 0.0, {"cached": True}
        start = time.time()
        rc = orch.run_tests_for_project(project)
        for _ in range(retries):
            if rc == 0:
                break
            rc = orch.run_tests_for_project(project)
        info["hash"] = hash_project(project)
        update_cache(project, "test", info, cache_mode)
        if cache_mode != "off" and rc == 0:
            write_artifact(project, "test", info)
        return name, rc, time.time() - start, info

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for name, rc, dur, info in pool.map(_run, names):
            entry = {"project": name, "rc": rc, "duration": dur}
            entry.update(info)
            results.append(entry)
            if rc != 0:
                failures.append(name)
            if progress_cb:
                try:
                    progress_cb(entry)
                except Exception:
                    pass
    return (0 if not failures else 1), results


def run_projects_serial(orch, projects, names, cache_mode: str = "off", retries: int = 0, progress_cb=None):
    results = []
    failures = []
    for name in names:
        project = projects[name]
        skip, info = should_skip_cached(project, "test", cache_mode)
        if skip:
            results.append({"project": name, "rc": 0, "duration": 0.0, "cached": True})
            continue
        start = time.time()
        rc = orch.run_tests_for_project(project)
        for _ in range(retries):
            if rc == 0:
                break
            rc = orch.run_tests_for_project(project)
        info["hash"] = hash_project(project)
        update_cache(project, "test", info, cache_mode)
        if cache_mode != "off" and rc == 0:
            write_artifact(project, "test", info)
        entry = {"project": name, "rc": rc, "duration": time.time() - start}
        entry.update(info)
        results.append(entry)
        if rc != 0:
            failures.append(name)
        if progress_cb:
            try:
                progress_cb(entry)
            except Exception:
                pass
    return (0 if not failures else 1), results
