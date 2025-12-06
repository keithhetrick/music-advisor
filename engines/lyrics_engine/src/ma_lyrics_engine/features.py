"""
Lyric feature extraction and related helpers.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ma_lyric_engine.utils import (
    PRONOUNS_1P,
    PRONOUNS_2P,
    PRONOUNS_3P,
    PROFANITY,
    THEME_LEXICON,
    clean_lyrics_text,
    count_syllables,
    rhyme_key,
    sectionize,
    tokenize_words,
)


def load_concreteness_lexicon(path: Optional[Path], log) -> Dict[str, float]:
    if not path:
        return {}
    if not path.exists():
        log(f"[WARN] Concreteness lexicon not found: {path}")
        return {}
    lex = {}
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = (row.get("Word") or row.get("word") or "").strip().lower()
            score_str = row.get("Conc.M") or row.get("concreteness") or row.get("score")
            if not word or not score_str:
                continue
            try:
                lex[word] = float(score_str)
            except ValueError:
                continue
    log(f"[INFO] Loaded concreteness lexicon entries: {len(lex)}")
    return lex


def load_vader():
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore

        return SentimentIntensityAnalyzer()
    except Exception:
        return None


def sentiment_scores(analyzer, text: str) -> Tuple[float, float, float, float]:
    if analyzer is None or not text.strip():
        return 0.0, 0.0, 0.0, 1.0
    scores = analyzer.polarity_scores(text)
    return (
        float(scores.get("compound", 0.0)),
        float(scores.get("pos", 0.0)),
        float(scores.get("neg", 0.0)),
        float(scores.get("neu", 0.0)),
    )


def sonic_texture_scores(words: List[str]) -> Tuple[float, float, float]:
    if not words:
        return 0.0, 0.0, 0.0
    initials = [w[0] for w in words if w]
    vowels = [re.sub(r"[^aeiou]", "", w) for w in words]
    consonants = [re.sub(r"[aeiou]", "", w) for w in words]

    def ratio(seq: List[str]) -> float:
        if not seq:
            return 0.0
        counts = Counter(seq)
        most = counts.most_common(1)[0][1]
        return round(most / max(1, len(seq)), 4)

    return ratio(initials), ratio([v for v in vowels if v]), ratio([c for c in consonants if c])


def theme_scores(words: List[str]) -> Dict[str, float]:
    counts = Counter(words)
    total = sum(counts.values()) or 1
    scores = {}
    for theme, lex in THEME_LEXICON.items():
        hits = sum(counts.get(token, 0) for token in lex)
        scores[theme] = round(hits / total, 4)
    return scores


def compute_features_for_song(
    analyzer,
    concreteness_lex: Dict[str, float],
    lyrics_id: str,
    song_id: str,
    clean_text: str,
    tempo_bpm: Optional[float],
    duration_ms: Optional[float],
) -> Dict[str, object]:
    sections, flat_lines = sectionize(clean_text)
    line_records = []
    feature_lines = []
    line_idx = 0
    rhyme_hist = Counter()
    explicit_lines = 0
    pronoun_counts = Counter()
    concreteness_scores: List[float] = []
    theme_aggr = Counter()
    sentiments = []
    words_total: List[str] = []
    for sec in sections:
        for line in sec["lines"]:
            line_idx += 1
            tokens = tokenize_words(line)
            words_total.extend(tokens)
            syllable_total = sum(count_syllables(t) for t in tokens)
            rk = rhyme_key(tokens[-1]) if tokens else ""
            rhyme_hist[rk] += 1
            internal_keys = [rhyme_key(t) for t in tokens if t]
            internal_flag = 1 if len(set(k for k in internal_keys if k)) < len(internal_keys) and len(internal_keys) > 1 else 0
            sentiment, pos, neg, neu = sentiment_scores(analyzer, line)
            sentiments.append(sentiment)
            explicit_flag = 1 if any(t in PROFANITY for t in tokens) else 0
            explicit_lines += explicit_flag
            p1 = sum(1 for t in tokens if t in PRONOUNS_1P)
            p2 = sum(1 for t in tokens if t in PRONOUNS_2P)
            p3 = sum(1 for t in tokens if t in PRONOUNS_3P)
            pronoun_counts["p1"] += p1
            pronoun_counts["p2"] += p2
            pronoun_counts["p3"] += p3
            allit, asson, conson = sonic_texture_scores(tokens)
            themes_line = theme_scores(tokens)
            if concreteness_lex:
                conc_vals = [concreteness_lex[t] for t in tokens if t in concreteness_lex]
                conc_line = float(sum(conc_vals) / len(conc_vals)) if conc_vals else 0.0
            else:
                conc_line = 0.0
            concreteness_scores.append(conc_line)
            for k, v in themes_line.items():
                theme_aggr[k] += v
            line_id = f"{lyrics_id}__line_{line_idx}"
            line_records.append(
                {
                    "line_id": line_id,
                    "lyrics_id": lyrics_id,
                    "section_label": sec["label"],
                    "line_number": line_idx,
                    "text": line,
                    "word_count": len(tokens),
                    "syllable_count": syllable_total,
                    "rhyme_key": rk,
                    "internal_rhyme_flag": internal_flag,
                }
            )
            feature_lines.append(
                {
                    "line_id": line_id,
                    "lyrics_id": lyrics_id,
                    "sentiment": sentiment,
                    "sentiment_pos": pos,
                    "sentiment_neg": neg,
                    "sentiment_neu": neu,
                    "explicit_flag": explicit_flag,
                    "pronoun_first": p1,
                    "pronoun_second": p2,
                    "pronoun_third": p3,
                    "alliteration": allit,
                    "assonance": asson,
                    "consonance": conson,
                    "concreteness": conc_line,
                    "themes": themes_line,
                }
            )
    total_words = len(words_total)
    lexical_diversity = float(len(set(words_total)) / total_words) if total_words else 0.0
    total_lines = len(line_records) or 1
    avg_words = sum(r["word_count"] for r in line_records) / total_lines
    avg_syllables = sum(r["syllable_count"] for r in line_records) / total_lines
    repetition_rate = 0.0
    if flat_lines:
        counts = Counter(flat_lines)
        repeated = sum(c for c in counts.values() if c > 1)
        repetition_rate = repeated / len(flat_lines)
    hook_density = repetition_rate
    rhyme_density = sum(c for c in rhyme_hist.values() if c > 1) / total_lines
    internal_rhyme_density = sum(r["internal_rhyme_flag"] for r in line_records) / total_lines
    explicit_fraction = explicit_lines / total_lines
    sentiment_mean = statistics.fmean(sentiments) if sentiments else 0.0
    sentiment_std = statistics.pstdev(sentiments) if len(sentiments) > 1 else 0.0
    theme_totals = {k: v / total_lines for k, v in theme_aggr.items()}
    concreteness_song = float(statistics.fmean(concreteness_scores)) if concreteness_scores else 0.0
    section_pattern = "-".join(sec["label"].split("_")[0][0] for sec in sections)
    tempo = float(tempo_bpm) if tempo_bpm is not None else None
    duration_sec = float(duration_ms) / 1000.0 if duration_ms is not None else None
    syllable_density = 0.0
    if duration_sec and duration_sec > 0:
        syllable_density = (sum(r["syllable_count"] for r in line_records) / duration_sec) / 4.0
    song_features = {
        "song_id": song_id,
        "lyrics_id": lyrics_id,
        "verse_count": sum(1 for s in sections if s["label"].startswith("VERSE")),
        "pre_count": sum(1 for s in sections if s["label"].startswith("PRE")),
        "chorus_count": sum(1 for s in sections if s["label"].startswith("CHORUS")),
        "bridge_count": sum(1 for s in sections if s["label"].startswith("BRIDGE")),
        "outro_count": sum(1 for s in sections if s["label"].startswith("OUTRO")),
        "section_pattern": section_pattern,
        "avg_words_per_line": avg_words,
        "avg_syllables_per_line": avg_syllables,
        "lexical_diversity": lexical_diversity,
        "repetition_rate": repetition_rate,
        "hook_density": hook_density,
        "sentiment_mean": sentiment_mean,
        "sentiment_std": sentiment_std,
        "pov_first": pronoun_counts["p1"] / (total_words or 1),
        "pov_second": pronoun_counts["p2"] / (total_words or 1),
        "pov_third": pronoun_counts["p3"] / (total_words or 1),
        "explicit_fraction": explicit_fraction,
        "rhyme_density": rhyme_density,
        "internal_rhyme_density": internal_rhyme_density,
        "concreteness": concreteness_song,
        "syllable_density": syllable_density,
        "tempo_bpm": tempo,
        "duration_sec": duration_sec,
    }
    for theme in THEME_LEXICON:
        song_features[f"theme_{theme}"] = round(theme_totals.get(theme, 0.0), 4)
    return {
        "sections": sections,
        "lines": line_records,
        "features_line": feature_lines,
        "features_song": song_features,
    }


def write_section_and_line_tables(
    conn: sqlite3.Connection,
    payload: Dict[str, object],
    lyrics_id: str,
) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM sections WHERE lyrics_id=?", (lyrics_id,))
    cur.execute("DELETE FROM lines WHERE lyrics_id=?", (lyrics_id,))
    cur.execute("DELETE FROM features_line WHERE lyrics_id=?", (lyrics_id,))
    sections = payload["sections"]
    line_records = payload["lines"]
    feature_lines = payload["features_line"]
    line_idx = 0
    for sec_idx, sec in enumerate(sections, start=1):
        start_line = line_idx + 1
        line_idx += len(sec["lines"])
        end_line = line_idx
        section_id = f"{lyrics_id}__sec_{sec_idx}"
        cur.execute(
            """
            INSERT INTO sections (section_id, lyrics_id, label, start_line, end_line)
            VALUES (?, ?, ?, ?, ?);
            """,
            (section_id, lyrics_id, sec["label"], start_line, end_line),
        )
    cur.executemany(
        """
        INSERT INTO lines
            (line_id, lyrics_id, section_label, line_number, text,
             word_count, syllable_count, rhyme_key, internal_rhyme_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                r["line_id"],
                r["lyrics_id"],
                r["section_label"],
                r["line_number"],
                r["text"],
                r["word_count"],
                r["syllable_count"],
                r["rhyme_key"],
                r["internal_rhyme_flag"],
            )
            for r in line_records
        ],
    )
    cur.executemany(
        """
        INSERT INTO features_line
            (line_id, lyrics_id, sentiment, sentiment_pos, sentiment_neg, sentiment_neu,
             explicit_flag, pronoun_first, pronoun_second, pronoun_third,
             alliteration, assonance, consonance, concreteness,
             theme_love, theme_heartbreak, theme_empowerment, theme_nostalgia,
             theme_flex, theme_spiritual, theme_family, theme_small_town)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                f["line_id"],
                f["lyrics_id"],
                f["sentiment"],
                f["sentiment_pos"],
                f["sentiment_neg"],
                f["sentiment_neu"],
                f["explicit_flag"],
                f["pronoun_first"],
                f["pronoun_second"],
                f["pronoun_third"],
                f["alliteration"],
                f["assonance"],
                f["consonance"],
                f["concreteness"],
                f["themes"].get("love", 0.0),
                f["themes"].get("heartbreak", 0.0),
                f["themes"].get("empowerment", 0.0),
                f["themes"].get("nostalgia", 0.0),
                f["themes"].get("flex", 0.0),
                f["themes"].get("spiritual", 0.0),
                f["themes"].get("family", 0.0),
                f["themes"].get("small_town", 0.0),
            )
            for f in feature_lines
        ],
    )
    conn.commit()


def write_song_features(conn: sqlite3.Connection, song_features: Dict[str, object]) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO features_song
            (song_id, lyrics_id, verse_count, pre_count, chorus_count, bridge_count,
             outro_count, section_pattern, avg_words_per_line, avg_syllables_per_line,
             lexical_diversity, repetition_rate, hook_density, sentiment_mean,
             sentiment_std, pov_first, pov_second, pov_third, explicit_fraction,
             rhyme_density, internal_rhyme_density, concreteness, theme_love,
             theme_heartbreak, theme_empowerment, theme_nostalgia, theme_flex,
             theme_spiritual, theme_family, theme_small_town, syllable_density,
             tempo_bpm, duration_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            song_features["song_id"],
            song_features["lyrics_id"],
            song_features["verse_count"],
            song_features["pre_count"],
            song_features["chorus_count"],
            song_features["bridge_count"],
            song_features["outro_count"],
            song_features["section_pattern"],
            song_features["avg_words_per_line"],
            song_features["avg_syllables_per_line"],
            song_features["lexical_diversity"],
            song_features["repetition_rate"],
            song_features["hook_density"],
            song_features["sentiment_mean"],
            song_features["sentiment_std"],
            song_features["pov_first"],
            song_features["pov_second"],
            song_features["pov_third"],
            song_features["explicit_fraction"],
            song_features["rhyme_density"],
            song_features["internal_rhyme_density"],
            song_features["concreteness"],
            song_features.get("theme_love", 0.0),
            song_features.get("theme_heartbreak", 0.0),
            song_features.get("theme_empowerment", 0.0),
            song_features.get("theme_nostalgia", 0.0),
            song_features.get("theme_flex", 0.0),
            song_features.get("theme_spiritual", 0.0),
            song_features.get("theme_family", 0.0),
            song_features.get("theme_small_town", 0.0),
            song_features.get("syllable_density", 0.0),
            song_features.get("tempo_bpm"),
            song_features.get("duration_sec"),
        ),
    )
    vector = [
        song_features["verse_count"],
        song_features["pre_count"],
        song_features["chorus_count"],
        song_features["bridge_count"],
        song_features["outro_count"],
        song_features["avg_words_per_line"],
        song_features["avg_syllables_per_line"],
        song_features["lexical_diversity"],
        song_features["repetition_rate"],
        song_features["hook_density"],
        song_features["sentiment_mean"],
        song_features["sentiment_std"],
        song_features["pov_first"],
        song_features["pov_second"],
        song_features["pov_third"],
        song_features["explicit_fraction"],
        song_features["rhyme_density"],
        song_features["internal_rhyme_density"],
        song_features["concreteness"],
        song_features.get("theme_love", 0.0),
        song_features.get("theme_heartbreak", 0.0),
        song_features.get("theme_empowerment", 0.0),
        song_features.get("theme_nostalgia", 0.0),
        song_features.get("theme_flex", 0.0),
        song_features.get("theme_spiritual", 0.0),
        song_features.get("theme_family", 0.0),
        song_features.get("theme_small_town", 0.0),
        song_features.get("syllable_density", 0.0),
    ]
    cur.execute(
        """
        INSERT OR REPLACE INTO features_song_vector (song_id, vector)
        VALUES (?, ?);
        """,
        (song_features["song_id"], json.dumps(vector)),
    )
    conn.commit()
