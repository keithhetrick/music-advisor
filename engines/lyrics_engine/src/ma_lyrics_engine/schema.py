"""
SQLite schema helpers for lyric intelligence.
"""
from __future__ import annotations

import sqlite3


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS songs (
            song_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            year INTEGER,
            peak_position INTEGER,
            weeks_on_chart INTEGER,
            source TEXT,
            tier INTEGER,
            era_bucket TEXT
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lyrics (
            lyrics_id TEXT PRIMARY KEY,
            song_id TEXT,
            raw_text TEXT,
            clean_text TEXT,
            source TEXT,
            FOREIGN KEY (song_id) REFERENCES songs(song_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sections (
            section_id TEXT PRIMARY KEY,
            lyrics_id TEXT,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            FOREIGN KEY (lyrics_id) REFERENCES lyrics(lyrics_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lines (
            line_id TEXT PRIMARY KEY,
            lyrics_id TEXT,
            section_label TEXT,
            line_number INTEGER,
            text TEXT,
            word_count INTEGER,
            syllable_count INTEGER,
            rhyme_key TEXT,
            internal_rhyme_flag INTEGER,
            FOREIGN KEY (lyrics_id) REFERENCES lyrics(lyrics_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_line (
            line_id TEXT PRIMARY KEY,
            lyrics_id TEXT,
            sentiment REAL,
            sentiment_pos REAL,
            sentiment_neg REAL,
            sentiment_neu REAL,
            explicit_flag INTEGER,
            pronoun_first INTEGER,
            pronoun_second INTEGER,
            pronoun_third INTEGER,
            alliteration REAL,
            assonance REAL,
            consonance REAL,
            concreteness REAL,
            theme_love REAL,
            theme_heartbreak REAL,
            theme_empowerment REAL,
            theme_nostalgia REAL,
            theme_flex REAL,
            theme_spiritual REAL,
            theme_family REAL,
            theme_small_town REAL,
            FOREIGN KEY (lyrics_id) REFERENCES lyrics(lyrics_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_song (
            song_id TEXT PRIMARY KEY,
            lyrics_id TEXT,
            verse_count INTEGER,
            pre_count INTEGER,
            chorus_count INTEGER,
            bridge_count INTEGER,
            outro_count INTEGER,
            section_pattern TEXT,
            avg_words_per_line REAL,
            avg_syllables_per_line REAL,
            lexical_diversity REAL,
            repetition_rate REAL,
            hook_density REAL,
            sentiment_mean REAL,
            sentiment_std REAL,
            pov_first REAL,
            pov_second REAL,
            pov_third REAL,
            explicit_fraction REAL,
            rhyme_density REAL,
            internal_rhyme_density REAL,
            concreteness REAL,
            theme_love REAL,
            theme_heartbreak REAL,
            theme_empowerment REAL,
            theme_nostalgia REAL,
            theme_flex REAL,
            theme_spiritual REAL,
            theme_family REAL,
            theme_small_town REAL,
            syllable_density REAL,
            tempo_bpm REAL,
            duration_sec REAL,
            FOREIGN KEY (lyrics_id) REFERENCES lyrics(lyrics_id),
            FOREIGN KEY (song_id) REFERENCES songs(song_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_song_lci (
            song_id TEXT PRIMARY KEY,
            lyrics_id TEXT,
            axis_structure REAL,
            axis_prosody REAL,
            axis_rhyme REAL,
            axis_lexical REAL,
            axis_pov REAL,
            axis_theme REAL,
            LCI_lyric_v1_raw REAL,
            LCI_lyric_v1_final_score REAL,
            profile TEXT,
            FOREIGN KEY (song_id) REFERENCES songs(song_id),
            FOREIGN KEY (lyrics_id) REFERENCES lyrics(lyrics_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_song_vector (
            song_id TEXT PRIMARY KEY,
            vector TEXT,
            FOREIGN KEY (song_id) REFERENCES songs(song_id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS features_ttc (
            song_id TEXT PRIMARY KEY,
            ttc_seconds_first_chorus REAL,
            ttc_bar_position_first_chorus REAL,
            estimation_method TEXT,
            profile TEXT,
            ttc_confidence TEXT,
            FOREIGN KEY (song_id) REFERENCES songs(song_id)
        );
        """
    )
    # Backfill missing columns on existing tables
    cur.execute("PRAGMA table_info(features_ttc);")
    cols = {row[1] for row in cur.fetchall()}
    if "ttc_confidence" not in cols:
        cur.execute("ALTER TABLE features_ttc ADD COLUMN ttc_confidence TEXT;")
    conn.commit()

__all__ = [
    "ensure_schema",
]
