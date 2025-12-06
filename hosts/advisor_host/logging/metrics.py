"""
Lightweight metrics helper (logging-based).
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

from advisor_host.logging.logger import log_event

PROM_ENABLED = os.getenv("HOST_PROM_ENABLED", "").lower() in ("1", "true", "yes")
PROM_COUNTER = None
PROM_HISTOGRAM = None

if PROM_ENABLED:
    try:
        from prometheus_client import Counter, Histogram  # type: ignore

        PROM_COUNTER = Counter("advisor_host_events_total", "Events emitted", ["metric"])
        PROM_HISTOGRAM = Histogram("advisor_host_latency_ms", "Latency (ms)", ["metric"])
    except Exception:
        PROM_COUNTER = None
        PROM_HISTOGRAM = None
        PROM_ENABLED = False


def record_metric(name: str, labels: Dict[str, Any] | None = None, value: float | int | None = None) -> None:
    """
    Emit a metrics-like log entry. This keeps us dependency-free while allowing
    downstream ingestion into real metrics systems.
    """
    payload: Dict[str, Any] = {"metric": name}
    if labels:
        payload.update({f"label_{k}": v for k, v in labels.items()})
    if value is not None:
        payload["value"] = value
    payload["ts"] = time.time()
    log_event("metric", payload)
    if PROM_ENABLED and PROM_COUNTER:
        try:
            PROM_COUNTER.labels(name).inc()
            if value is not None and PROM_HISTOGRAM:
                PROM_HISTOGRAM.labels(name).observe(float(value))
        except Exception:
            pass


def timing_ms(start: float) -> float:
    return (time.time() - start) * 1000.0


def make_correlated_labels(base: Dict[str, Any], correlation_id: str | None) -> Dict[str, Any]:
    lbls = dict(base)
    if correlation_id:
        lbls["correlation_id"] = correlation_id
    return lbls
