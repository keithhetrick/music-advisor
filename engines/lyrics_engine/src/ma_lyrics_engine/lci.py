"""
Lyric Confidence Index (LCI) axes, scoring, and calibration utilities.
"""
from __future__ import annotations

import csv
import json
import math
import sqlite3
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ma_lyric_engine.utils import slugify_song
from ma_config.constants import LCI_AXES

CANONICAL_AXES = LCI_AXES


def clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def load_calibration(path: Path) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "axes" not in data:
        raise ValueError("Calibration file missing 'axes' block")
    return data


def axis_score(raw: float, cfg: Dict[str, float]) -> float:
    mu = float(cfg.get("mu", 0.0))
    sigma = float(cfg.get("sigma", 1.0)) or 1.0
    clip = float(cfg.get("clip", 3.0)) or 3.0
    z = (raw - mu) / sigma
    dist = min(abs(z), clip)
    return clamp01(1.0 - dist / clip)


def weighted_axis_mean(axis_scores: Dict[str, float], axes_cfg: Dict[str, Dict[str, float]]) -> float:
    total_weight = 0.0
    acc = 0.0
    for axis, score in axis_scores.items():
        weight = float(axes_cfg.get(axis, {}).get("weight", 1.0) or 1.0)
        total_weight += weight
        acc += score * weight
    if total_weight == 0:
        return 0.0
    return acc / total_weight


def score_axes_to_lci(
    axis_raws: Dict[str, float],
    calibration: Dict[str, object],
    profile: str,
) -> Tuple[Dict[str, float], float, float]:
    axes_cfg = calibration.get("axes", {}) or {}
    axis_scores = {axis: axis_score(axis_raws.get(axis, 0.0), axes_cfg.get(axis, {})) for axis in axis_raws}
    lci_raw = weighted_axis_mean(axis_scores, axes_cfg)
    agg_cfg = calibration.get("aggregation", {}) or {}
    target_mu = float(agg_cfg.get("target_mu", lci_raw))
    target_sigma = float(agg_cfg.get("target_sigma", 0.0))
    if target_sigma > 0:
        z = (lci_raw - target_mu) / target_sigma
        lci_final = 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
    else:
        lci_final = lci_raw
    lci_final = clamp01(lci_final)
    return axis_scores, lci_raw, lci_final


def compute_axis_raws(features_row: Dict[str, object], calibration: Optional[Dict[str, object]] = None) -> Dict[str, float]:
    verse = float(features_row.get("verse_count") or 0.0)
    pre = float(features_row.get("pre_count") or 0.0)
    chorus = float(features_row.get("chorus_count") or 0.0)
    bridge = float(features_row.get("bridge_count") or 0.0)
    outro = float(features_row.get("outro_count") or 0.0)
    section_pattern = (features_row.get("section_pattern") or "").strip()
    repetition_rate = float(features_row.get("repetition_rate") or 0.0)
    hook_density = float(features_row.get("hook_density") or 0.0)
    avg_words_per_line = float(features_row.get("avg_words_per_line") or 0.0)
    avg_syllables_per_line = float(features_row.get("avg_syllables_per_line") or 0.0)
    syllable_density = float(features_row.get("syllable_density") or 0.0)
    lexical_diversity = float(features_row.get("lexical_diversity") or 0.0)
    explicit_fraction = float(features_row.get("explicit_fraction") or 0.0)
    rhyme_density = float(features_row.get("rhyme_density") or 0.0)
    internal_rhyme_density = float(features_row.get("internal_rhyme_density") or 0.0)
    pov_first = float(features_row.get("pov_first") or 0.0)
    pov_second = float(features_row.get("pov_second") or 0.0)
    pov_third = float(features_row.get("pov_third") or 0.0)
    concreteness = float(features_row.get("concreteness") or 0.0)
    theme_keys = [
        "theme_love",
        "theme_heartbreak",
        "theme_empowerment",
        "theme_nostalgia",
        "theme_flex",
        "theme_spiritual",
        "theme_family",
        "theme_small_town",
    ]
    theme_vals = [float(features_row.get(k) or 0.0) for k in theme_keys]

    total_sections = verse + pre + chorus + bridge + outro
    section_tokens = [tok for tok in section_pattern.split("-") if tok]
    components = {
        "section_count": clamp01(total_sections / 8.0),
        "section_diversity": clamp01(len(set(section_tokens)) / len(section_tokens)) if section_tokens else 0.0,
        "hook_texture": clamp01((hook_density + repetition_rate) / 2.0),
        "words_score": clamp01(avg_words_per_line / 12.0),
        "syll_score": clamp01(avg_syllables_per_line / 16.0),
        "density_score": clamp01(syllable_density / 3.0),
        "rhyme_density": clamp01(rhyme_density),
        "internal_rhyme": clamp01(internal_rhyme_density),
        "lexical_diversity": clamp01(lexical_diversity),
        "verbosity": clamp01(avg_words_per_line / 12.0),
        "explicit_restraint": clamp01(1.0 - explicit_fraction),
        "pov_presence": clamp01((pov_first + pov_second + pov_third) * 4.0),
        "pov_balance": 0.0,
        "theme_mean": statistics.fmean(theme_vals) if theme_vals else 0.0,
        "concreteness": clamp01(concreteness),
        "sentiment_level": clamp01(((features_row.get("sentiment_mean") or 0.0) + 1.0) / 2.0),
    }
    pov_total = pov_first + pov_second + pov_third
    if pov_total > 0:
        shares = [pov_first / pov_total, pov_second / pov_total, pov_third / pov_total]
        components["pov_balance"] = clamp01(1.0 - (max(shares) - min(shares)))

    axis_defs = (calibration or {}).get("axes", {}) if calibration else {}

    def blend(axis_name: str, defaults: Dict[str, float]) -> float:
        cfg = axis_defs.get(axis_name, {})
        weights = cfg.get("component_weights", defaults)
        total_w = sum(weights.values()) or sum(defaults.values())
        score = 0.0
        for comp, w in (weights or defaults).items():
            score += components.get(comp, 0.0) * w
        return clamp01(score / total_w) if total_w else 0.0

    axis_structure = blend(
        "structure_fit",
        {"section_count": 0.3, "section_diversity": 0.3, "hook_texture": 0.4},
    )
    axis_prosody = blend("prosody_ttc_fit", {"words_score": 1.0, "syll_score": 1.0, "density_score": 1.0})
    axis_rhyme = blend("rhyme_texture_fit", {"rhyme_density": 0.6, "internal_rhyme": 0.4})
    axis_diction = blend(
        "diction_style_fit",
        {"lexical_diversity": 0.6, "verbosity": 0.2, "explicit_restraint": 0.2, "sentiment_level": 0.0},
    )
    axis_pov = blend("pov_fit", {"pov_balance": 0.6, "pov_presence": 0.4})
    axis_theme = blend("theme_fit", {"theme_mean": 0.7, "concreteness": 0.3})

    return {
        "structure_fit": axis_structure,
        "prosody_ttc_fit": axis_prosody,
        "rhyme_texture_fit": axis_rhyme,
        "diction_style_fit": axis_diction,
        "pov_fit": axis_pov,
        "theme_fit": axis_theme,
    }


def upsert_features_song_lci(
    conn: sqlite3.Connection,
    song_id: str,
    lyrics_id: Optional[str],
    axis_scores: Dict[str, float],
    lci_raw: float,
    lci_final: float,
    profile: str,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO features_song_lci
            (song_id, lyrics_id, axis_structure, axis_prosody, axis_rhyme,
             axis_lexical, axis_pov, axis_theme, LCI_lyric_v1_raw,
             LCI_lyric_v1_final_score, profile)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            song_id,
            lyrics_id,
            axis_scores.get("structure_fit"),
            axis_scores.get("prosody_ttc_fit"),
            axis_scores.get("rhyme_texture_fit"),
            axis_scores.get("diction_style_fit"),
            axis_scores.get("pov_fit"),
            axis_scores.get("theme_fit"),
            lci_raw,
            lci_final,
            profile,
        ),
    )
    conn.commit()


def fetch_features_row(conn: sqlite3.Connection, song_id: str) -> Optional[Dict[str, object]]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM features_song WHERE song_id=?", (song_id,))
    row = cur.fetchone()
    if not row:
        return None
    return {k: row[k] for k in row.keys()}


def compute_lci_for_song(
    conn: sqlite3.Connection,
    song_id: str,
    profile: Optional[str],
    calibration_path: Optional[Path] = None,
    calibration: Optional[Dict[str, object]] = None,
    log=print,
) -> bool:
    if calibration is None:
        if calibration_path is None:
            raise ValueError("calibration_path is required when calibration dict is not provided.")
        calibration = load_calibration(calibration_path)
    if not profile:
        profile = calibration.get("calibration_profile") or calibration.get("profile")
    row = fetch_features_row(conn, song_id)
    if not row:
        log(f"[WARN] No features_song row for song_id={song_id}; skipping LCI.")
        return False
    axis_raws = compute_axis_raws(row, calibration=calibration)
    axis_scores, lci_raw, lci_final = score_axes_to_lci(axis_raws, calibration, profile)
    upsert_features_song_lci(conn, song_id, row.get("lyrics_id"), axis_scores, lci_raw, lci_final, profile)
    return True


def iter_song_ids_for_scoring(conn: sqlite3.Connection, song_id: Optional[str], limit: Optional[int]) -> Iterable[str]:
    cur = conn.cursor()
    if song_id:
        yield song_id
        return
    sql = "SELECT song_id FROM features_song"
    params: tuple[object, ...] = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    for row in cur.execute(sql, params):
        yield row[0]


def build_calibration(
    conn: sqlite3.Connection,
    core_csv: Optional[Path],
    profile: str,
    out_path: Path,
    log,
) -> Dict[str, object]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if core_csv and core_csv.exists():
        log(f"[INFO] Using core cohort CSV for calibration: {core_csv}")
        song_ids: List[str] = []
        with core_csv.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title") or row.get("Song") or ""
                artist = row.get("artist") or row.get("Artist") or ""
                try:
                    year = int(row.get("year") or row.get("Year") or 0)
                except Exception:
                    year = None
                slug = slugify_song(title, artist, year)
                song_ids.append(slug)
        if not song_ids:
            raise SystemExit("[ERROR] No cohort rows found in core CSV.")
        cur.execute(
            f"SELECT * FROM features_song WHERE song_id IN ({','.join('?' for _ in song_ids)})",
            song_ids,
        )
        rows = cur.fetchall()
    else:
        log("[INFO] Using all features_song rows for calibration.")
        cur.execute("SELECT * FROM features_song")
        rows = cur.fetchall()

    if not rows:
        raise SystemExit("[ERROR] No rows available for calibration.")

    axis_raw_list: List[Dict[str, float]] = []
    for row in rows:
        row_dict = {k: row[k] for k in row.keys()}
        axis_raw_list.append(compute_axis_raws(row_dict))

    axes_cfg: Dict[str, Dict[str, float]] = {}
    for axis in CANONICAL_AXES:
        values = [r[axis] for r in axis_raw_list]
        mu = statistics.fmean(values)
        sigma = statistics.pstdev(values) if len(values) > 1 else 1.0
        axes_cfg[axis] = {"mu": mu, "sigma": sigma or 1.0, "clip": 3.0, "weight": 1.0}

    calibration = {
        "version": "LCI_lyric_v1",
        "profile": profile,
        "calibration_profile": profile,
        "axes": axes_cfg,
        "aggregation": {
            "method": "weighted_mean",
            "target_mu": 0.0,
            "target_sigma": 0.0,
        },
    }

    lci_raw_values: List[float] = []
    for axis_raws in axis_raw_list:
        axis_scores = {axis: axis_score(axis_raws.get(axis, 0.0), axes_cfg[axis]) for axis in axes_cfg}
        lci_raw_values.append(weighted_axis_mean(axis_scores, axes_cfg))
    if lci_raw_values:
        calibration["aggregation"]["target_mu"] = statistics.fmean(lci_raw_values)
        calibration["aggregation"]["target_sigma"] = (
            statistics.pstdev(lci_raw_values) if len(lci_raw_values) > 1 else 0.1
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    log(f"[INFO] Wrote calibration JSON to {out_path}")
    return calibration

__all__ = [
    "axis_score",
    "build_calibration",
    "clamp01",
    "compute_axis_raws",
    "compute_lci_for_song",
    "fetch_features_row",
    "iter_song_ids_for_scoring",
    "load_calibration",
    "score_axes_to_lci",
    "upsert_features_song_lci",
    "weighted_axis_mean",
]
