from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from shared.ma_utils.schema_utils import lint_json_file
from ma_audio_engine.adapters import LOG_REDACT, LOG_REDACT_VALUES, make_logger
from tools import names

PHILOSOPHY_PAYLOAD: Dict[str, str] = {
    "tagline": "The Top 40 of today is the Top 40 of ~40 years ago, re-parameterized.",
    "summary": (
        "HCI_v1 is a measure of Historical Echo — not a hit predictor. "
        "It describes how this audio's 6D axes align with the audio patterns "
        "of successful US Pop songs (~1985–2024) and does not guarantee future "
        "success or provide a \"hitness\" verdict. Trend and market_norm layers "
        "live on top of HCI_v1 as optimization advice for the current landscape; "
        "they never override or replace HCI_v1 scores."
    ),
}

_log = make_logger("philosophy_services", redact=LOG_REDACT, secrets=LOG_REDACT_VALUES)


def inject_philosophy_into_hci(data: Dict[str, Any], *, force: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """Return updated HCI payload with philosophy block; warnings if lint fails."""
    if not isinstance(data, dict):
        return data, ["invalid:payload_not_object"]
    if "HCI_v1_philosophy" in data and not force:
        return data, []
    data = dict(data)
    data["HCI_v1_philosophy"] = PHILOSOPHY_PAYLOAD
    return data, []


def write_hci_with_philosophy(path: Path, force: bool = False) -> Tuple[bool, List[str]]:
    warns: List[str] = []
    try:
        payload = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        return False, [f"{path.name}:read_error:{e}"]
    updated, inject_warns = inject_philosophy_into_hci(payload, force=force)
    warns.extend([f"{path.name}:{w}" for w in inject_warns])
    try:
        path.write_text(json.dumps(updated, indent=2))
    except Exception as e:  # noqa: BLE001
        return False, [f"{path.name}:write_error:{e}"]
    lint_warns, _ = lint_json_file(path, "hci")
    warns.extend([f"{path.name}:{w}" for w in lint_warns])
    return True, warns


def inject_philosophy_line_into_client(text: str, philosophy_line: str) -> str:
    """Insert philosophy line into client rich text if not already present."""
    if "PHILOSOPHY:" in text:
        return text
    lines = text.splitlines()
    out: List[str] = []
    inserted = False
    for l in lines:
        out.append(l)
        if l.startswith("# HCI_V1_SUMMARY") and not inserted:
            out.append("")
            out.append(philosophy_line)
            out.append("")
            out.append("")
            inserted = True
    if not inserted:
        out = [philosophy_line, "", "", *out]
    return "\n".join(out).rstrip() + "\n"


def build_philosophy_line(default_tagline: str, hci_path: Path | None = None) -> str:
    tagline = default_tagline
    if hci_path and hci_path.exists():
        try:
            data = json.loads(hci_path.read_text())
            if isinstance(data, dict):
                philos = data.get("HCI_v1_philosophy")
                if isinstance(philos, dict):
                    t = philos.get("tagline") or philos.get("tagline_long")
                    if isinstance(t, str) and t.strip():
                        tagline = t.strip()
        except Exception:
            pass
    return (
        f"# PHILOSOPHY: {tagline} "
        "HCI_v1 is a measure of Historical Echo — not a hit predictor."
    )


def write_client_with_philosophy(client_path: Path, default_tagline: str = PHILOSOPHY_PAYLOAD["tagline"]) -> Tuple[bool, List[str]]:
    warns: List[str] = []
    try:
        text = client_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"{client_path.name}:read_error:{e}"]
    hci_path = client_path.with_name(client_path.name.replace(names.client_rich_suffix(), ".hci.json"))
    line = build_philosophy_line(default_tagline, hci_path if hci_path.name != client_path.name else None)
    new_text = inject_philosophy_line_into_client(text, line)
    if new_text == text:
        return False, []
    try:
        client_path.write_text(new_text, encoding="utf-8")
    except Exception as e:
        return False, [f"{client_path.name}:write_error:{e}"]
    lint_warns, _ = lint_json_file(client_path, "client_rich")
    warns.extend([f"{client_path.name}:{w}" for w in lint_warns])
    return True, warns

__all__ = [
    "build_philosophy_line",
    "inject_philosophy_into_hci",
    "inject_philosophy_line_into_client",
    "write_client_with_philosophy",
    "write_hci_with_philosophy",
]
