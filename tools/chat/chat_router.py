"""
High-level chat router that wires intents to overlay responders.
Modular: relies on loaders/dispatchers; does not recompute metrics.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional

from tools.chat.chat_context import ChatSession
from tools.chat.chat_intents import classify_intent
from tools.chat.chat_overlay_dispatcher import handle_intent as overlay_handle_intent
from tools.chat.paraphrase import env_paraphrase_enabled


def _safe_load(path: Path) -> Optional[Dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _maybe_paraphrase(session: ChatSession, reply: str) -> str:
    if not env_paraphrase_enabled():
        return reply
    pf = session.extras.get("paraphrase_fn") if isinstance(session.extras, dict) else None
    if callable(pf):
        try:
            return pf(reply)
        except Exception:
            return reply
    return reply


def _clamp_length(session: ChatSession, reply: str) -> str:
    max_len = session.max_length or 0
    if max_len <= 0:
        return reply
    if len(reply) <= max_len:
        return reply
    return reply[: max_len - 15] + "... [truncated]"


def _parse_top_n(message: str, default: int) -> int:
    try:
        import re
        m = re.search(r"top\\s*(\\d+)", message.lower())
        if m:
            return max(1, int(m.group(1)))
        nums = re.findall(r"(\\d+)", message)
        if nums:
            return max(1, int(nums[0]))
    except Exception:
        pass
    return default


def _parse_tier_filter(message: str) -> Optional[str]:
    m = re.search(r"tier\\s*([123])", message.lower())
    if m:
        return f"tier{m.group(1)}"
    return None


def _neighbors_summary(client_path: Path, top_n: int = 3, cache: Optional[dict] = None, tier_filter: Optional[str] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    neigh_path = base / f"{stem}.neighbors.json"
    # crude keyword filter for tier in cache key
    key = f"neighbors:{neigh_path}"
    if cache is not None and key in cache:
        data = cache[key]
    else:
        if not neigh_path.exists():
            return "Neighbors not available for this song."
        data = _safe_load(neigh_path) or {}
        if cache is not None:
            cache[key] = data
    neighbors = data.get("neighbors") or []
    if not neighbors:
        return "Neighbors not available for this song."
    lines = []
    filtered = []
    for nb in neighbors:
        if tier_filter and str(nb.get("tier", "")).lower() != tier_filter:
            continue
        filtered.append(nb)
    for nb in filtered[:top_n]:
        artist = str(nb.get("artist", "?"))[:30]
        title = str(nb.get("title", "?"))[:40]
        lines.append(
            f"{artist} — {title} ({nb.get('year','?')}, tier={nb.get('tier','?')}, dist={nb.get('distance',0):.3f})"
        )
    return "Neighbors: " + " | ".join(lines)


def _hci_summary(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    hci_files = sorted(base.glob(f"{stem}*.hci.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not hci_files:
        return "HCI not available for this song."
    key = f"hci:{hci_files[0]}"
    if cache is not None and key in cache:
        data = cache[key]
    else:
        data = _safe_load(hci_files[0]) or {}
        if cache is not None:
            cache[key] = data
    score = (
        data.get("HCI_v1_final_score")
        or (data.get("HCI_v1") or {}).get("final_score")
        or (data.get("HCI_audio_v2") or {}).get("final_score")
    )
    role = data.get("HCI_v1_role") or (data.get("HCI_v1") or {}).get("role")
    hem = data.get("historical_echo_meta") or {}
    primary_decade = hem.get("primary_decade") or (hem.get("primary_decade_counts") or None)
    parts = []
    if score is not None:
        parts.append(f"score={score}")
    if role:
        parts.append(f"role={role}")
    if primary_decade:
        parts.append(f"primary_decade={primary_decade}")
    return "HCI: " + (" | ".join(parts) if parts else "not available")


def _ttc_summary(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    ttc_files = sorted(base.glob(f"{stem}*.ttc.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ttc_files:
        return "TTC not available for this song."
    key = f"ttc:{ttc_files[0]}"
    if cache is not None and key in cache:
        data = cache[key]
    else:
        data = _safe_load(ttc_files[0]) or {}
        if cache is not None:
            cache[key] = data
    sec = data.get("ttc_seconds_first_chorus")
    status = data.get("status") or data.get("ttc_status")
    if sec is None and status:
        return f"TTC status: {status}"
    if sec is None:
        return "TTC not available for this song."
    bars = data.get("ttc_bars_first_chorus")
    return f"TTC: {sec} sec to first chorus" + (f" ({bars} bars)" if bars else "")


def _qa_summary(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    feat_files = sorted(base.glob(f"{stem}*.features.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not feat_files:
        return "QA not available for this song."
    key = f"qa:{feat_files[0]}"
    if cache is not None and key in cache:
        data = cache[key]
    else:
        data = _safe_load(feat_files[0]) or {}
        if cache is not None:
            cache[key] = data
    qa = data.get("qa") or {}
    gate = data.get("qa_gate")
    parts = []
    if qa.get("status"):
        parts.append(f"qa_status={qa.get('status')}")
    if qa.get("clipping") is not None:
        parts.append(f"clipping={qa.get('clipping')}")
    if qa.get("silence_ratio") is not None:
        parts.append(f"silence_ratio={qa.get('silence_ratio')}")
    if gate:
        parts.append(f"qa_gate={gate}")
    return "QA: " + (" | ".join(parts) if parts else "not available")


def _artifacts_summary(client_path: Path) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    files = {
        "tempo_norms": base / f"{stem}.tempo_norms.json",
        "key_norms": base / f"{stem}.key_norms.json",
        "neighbors": base / f"{stem}.neighbors.json",
        "hci": None,
        "features": None,
    }
    hci_files = sorted(base.glob(f"{stem}*.hci.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    feat_files = sorted(base.glob(f"{stem}*.features.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    files["hci"] = hci_files[0] if hci_files else None
    files["features"] = feat_files[0] if feat_files else None
    parts = []
    for name, path in files.items():
        if path and path.exists():
            parts.append(f"{name}: {path.name} ({path.stat().st_size} bytes)")
        else:
            parts.append(f"{name}: missing")
    return "Artifacts: " + " | ".join(parts)


def _metadata_summary(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    feat_files = sorted(base.glob(f"{stem}*.features.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not feat_files:
        return "Metadata not available for this song."
    key = f"meta:{feat_files[0]}"
    if cache is not None and key in cache:
        data = cache[key]
    else:
        data = _safe_load(feat_files[0]) or {}
        if cache is not None:
            cache[key] = data
    duration = data.get("duration_sec")
    codec = (data.get("source_audio_info") or {}).get("orig_format")
    size = (base / f"{stem}.sidecar.json").stat().st_size if (base / f"{stem}.sidecar.json").exists() else None
    parts = []
    if duration:
        parts.append(f"duration={duration:.1f}s")
    if codec:
        parts.append(f"codec={codec}")
    if size:
        parts.append(f"sidecar_bytes={size}")
    return "Metadata: " + (" | ".join(parts) if parts else "not available")


def _lane_summary(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    tempo_path = base / f"{stem}.tempo_norms.json"
    key_path = base / f"{stem}.key_norms.json"
    tempo = _safe_load(tempo_path) if tempo_path.exists() else None
    key = _safe_load(key_path) if key_path.exists() else None
    parts = []
    if tempo:
        ls = tempo.get("lane_stats") or {}
        parts.append(
            f"tempo_hot_zone={ls.get('peak_cluster_bpm_range')} (~{(ls.get('peak_cluster_percent_of_lane') or 0)*100:.1f}% lane) shape={ls.get('shape')}"
        )
    if key:
        ks = key.get("lane_stats") or {}
        parts.append(
            f"key_primary_family={ks.get('primary_family')} mode_split={ks.get('lane_shape',{}).get('mode_split')}"
        )
    return " | ".join(parts) if parts else "Lane summary not available."


def _key_targets(client_path: Path, cache: Optional[dict] = None, top_n: int = 3) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    key_path = base / f"{stem}.key_norms.json"
    if not key_path.exists():
        return "Key targets not available."
    data = _safe_load(key_path) or {}
    targets = (data.get("advisory") or {}).get("target_key_moves") or []
    if not targets:
        return "Key targets not available."
    lines = []
    for m in targets[:top_n]:
        tags = ";".join((m.get("rationale_tags") or [])[:3])
        lines.append(
            f"{m.get('target_key')} ({'+' if m.get('semitone_delta',0)>0 else ''}{m.get('semitone_delta',0)} st, {m.get('lane_percent',0)*100:.1f}% lane, tags={tags})"
        )
    return "Key targets: " + " | ".join(lines)


def _tempo_targets(client_path: Path, cache: Optional[dict] = None) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    tempo_path = base / f"{stem}.tempo_norms.json"
    if not tempo_path.exists():
        return "Tempo targets not available."
    data = _safe_load(tempo_path) or {}
    adv = data.get("advisory_text")
    rng = (data.get("lane_stats") or {}).get("peak_cluster_bpm_range")
    if not rng:
        return "Tempo targets not available."
    return f"Tempo nudge: toward {rng[0]:.1f}–{rng[1]:.1f} BPM. {adv or ''}"


def _why_summary(client_path: Path, last_intent: Optional[str]) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    if last_intent == "tempo":
        tempo_path = base / f"{stem}.tempo_norms.json"
        if tempo_path.exists():
            data = _safe_load(tempo_path) or {}
            return data.get("advisory_text") or "Tempo advisory not available."
        return "Tempo advisory not available."
    if last_intent == "key":
        key_path = base / f"{stem}.key_norms.json"
        if key_path.exists():
            data = _safe_load(key_path) or {}
            adv = (data.get("advisory") or {}).get("advisory_text")
            return adv or "Key advisory not available."
        return "Key advisory not available."
    return "No prior tempo/key intent to explain."


def _compare_summary(client_path: Path) -> str:
    base = client_path.parent
    stem = client_path.name.replace(".client.rich.txt", "")
    tempo_path = base / f"{stem}.tempo_norms.json"
    key_path = base / f"{stem}.key_norms.json"
    parts = []
    if tempo_path.exists():
        t = _safe_load(tempo_path) or {}
        lane_stats = t.get("lane_stats") or {}
        song_bpm = t.get("song_bpm")
        median = lane_stats.get("median_bpm")
        hot = lane_stats.get("peak_cluster_bpm_range")
        peak_pct = (lane_stats.get("peak_cluster_percent_of_lane") or 0) * 100
        if song_bpm and median and hot:
            parts.append(
                f"Tempo: {song_bpm:.1f} BPM vs lane median {median:.1f}, hot zone {hot[0]:.1f}–{hot[1]:.1f} BPM (~{peak_pct:.1f}% lane)."
            )
    if key_path.exists():
        k = _safe_load(key_path) or {}
        lane_stats = k.get("lane_stats") or {}
        song = k.get("song_placement") or {}
        family = lane_stats.get("primary_family") or []
        same_pct = (song.get("same_key_percent") or 0) * 100
        mode_pct = (song.get("same_mode_percent") or 0) * 100
        parts.append(
            f"Key: family {family[:3]} | same key ~{same_pct:.1f}% | same mode ~{mode_pct:.1f}%."
        )
    return " ".join(parts) if parts else "Compare not available."


def _fallback_summary(session: ChatSession) -> str:
    """
    Generic summary fallback when intent is unknown.
    Attempts to read the .client.rich.txt and return a trimmed excerpt with basic artifact hints.
    """
    path = session.client_path
    if not path or not path.exists():
        return "Context missing or unreadable; please provide a .client.rich.txt path."
    try:
        text = path.read_text()
        excerpt = text.strip().replace("\r", " ").replace("\n\n", "\n")
        if len(excerpt) > 1200:
            excerpt = excerpt[:1200] + "... [truncated]"
    except Exception:
        excerpt = "Could not read .client.rich.txt content."

    base = path.parent
    stem = path.name.replace(".client.rich.txt", "")
    flags = []
    if (base / f"{stem}.tempo_norms.json").exists():
        flags.append("tempo")
    if (base / f"{stem}.key_norms.json").exists():
        flags.append("key")
    if (base / f"{stem}.neighbors.json").exists():
        flags.append("neighbors")
    if any(base.glob(f"{stem}*.hci.json")):
        flags.append("hci")
    flag_str = f"Artifacts present: {', '.join(flags)}" if flags else "No tempo/key/neighbor/HCI artifacts found."
    return f"{flag_str}\n\nExcerpt:\n{excerpt}"


def route_message(session: ChatSession, message: str, client_path: Optional[Path] = None) -> str:
    """
    Route a chat message. If client_path is provided, set it on the session.
    """
    if client_path:
        session.set_client_path(client_path)
    if not session.client_path:
        return "No song context set; please provide a .client.rich.txt path."
    prev_intent = session.last_intent
    intent_model = session.extras.get("intent_model") if isinstance(session.extras, dict) else None
    intent = classify_intent(message, intent_model=intent_model)
    session.last_intent = intent.intent
    if "details" in message.lower() and prev_intent in ("tempo", "key"):
        session.detail = "verbose"
        reply = overlay_handle_intent(prev_intent, session.client_path, detail=session.detail)
        session.last_reply = reply
        session.history.append(reply)
        return reply
    if intent.intent == "help":
        reply = "Ask about: tempo, key, neighbors, HCI, TTC, QA, status. Add 'verbose' for more detail."
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "legend":
        reply = "legend: st=semitones, w=weight, c5=circle-of-fifths distance, tags=rationale tags"
        session.last_reply = reply
        session.history.append(reply)
        return reply
    if intent.intent == "context":
        reply = f"context: path={session.client_path} | detail={session.detail} | last_intent={session.last_intent}"
        session.last_reply = reply
        session.history.append(reply)
        return reply
    if "verbose" in message.lower():
        session.detail = "verbose"
    if "summary" in message.lower():
        session.detail = "summary"
    if intent.intent in ("tempo", "key"):
        reply = overlay_handle_intent(intent.intent, session.client_path, detail=session.detail)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "metadata":
        reply = _metadata_summary(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "lane_summary":
        reply = _lane_summary(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "key_targets":
        top_n = _parse_top_n(message, 3)
        reply = _key_targets(session.client_path, cache=session.cache, top_n=top_n)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "tempo_targets":
        reply = _tempo_targets(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "why":
        reply = _why_summary(session.client_path, prev_intent)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "compare":
        reply = _compare_summary(session.client_path)
        session.last_reply = reply
        session.history.append(reply)
        return reply
    if intent.intent == "neighbors":
        top_n = _parse_top_n(message, 3)
        tier_filter = _parse_tier_filter(message)
        reply = _neighbors_summary(session.client_path, cache=session.cache, top_n=top_n, tier_filter=tier_filter)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "hci":
        reply = _hci_summary(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "ttc":
        reply = _ttc_summary(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "qa":
        reply = _qa_summary(session.client_path, cache=session.cache)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "artifacts":
        reply = _artifacts_summary(session.client_path)
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    if intent.intent == "status":
        base = session.client_path.parent
        stem = session.client_path.name.replace(".client.rich.txt", "")
        files = {
            "tempo_norms": (base / f"{stem}.tempo_norms.json").exists(),
            "key_norms": (base / f"{stem}.key_norms.json").exists(),
            "neighbors": (base / f"{stem}.neighbors.json").exists(),
            "hci": any(base.glob(f"{stem}*.hci.json")),
        }
        missing = [k for k, v in files.items() if not v]
        if missing:
            reply = f"Missing artifacts: {', '.join(missing)}"
        else:
            reply = "Artifacts present for tempo/key/neighbors/hci."
        session.last_reply = reply
        session.history.append(reply)
        return _clamp_length(session, _maybe_paraphrase(session, reply))
    # Fallback generic summary from the .client.rich.txt so users are not stuck.
    reply = _fallback_summary(session)
    session.last_reply = reply
    session.history.append(reply)
    return _clamp_length(session, _maybe_paraphrase(session, reply))


__all__ = ["route_message"]
