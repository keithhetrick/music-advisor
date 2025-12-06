"""
Lyric neighbors utility over features_song_vector using cosine similarity.
"""
from __future__ import annotations

import json
import math
import sqlite3
from typing import Dict, List, Tuple


def cosine_sim(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def euclidean_sim(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    return 1.0 / (1.0 + dist)


def load_vectors(conn: sqlite3.Connection) -> Dict[str, Tuple[List[float], Dict[str, object]]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.song_id, s.title, s.artist, s.year, v.vector
        FROM features_song_vector v
        JOIN songs s ON s.song_id = v.song_id
        """
    )
    data: Dict[str, Tuple[List[float], Dict[str, object]]] = {}
    for row in cur.fetchall():
        song_id, title, artist, year, vec = row
        try:
            vector = [float(x) for x in json.loads(vec)]
        except Exception:
            continue
        meta = {"song_id": song_id, "title": title, "artist": artist, "year": year}
        data[song_id] = (vector, meta)
    return data


def nearest_neighbors(conn: sqlite3.Connection, song_id: str, limit: int = 5, distance: str = "cosine") -> List[Dict[str, object]]:
    data = load_vectors(conn)
    if song_id not in data:
        return []
    target_vec, _ = data[song_id]
    sims: List[Tuple[float, Dict[str, object]]] = []
    metric = cosine_sim if distance == "cosine" else euclidean_sim
    for sid, (vec, meta) in data.items():
        if sid == song_id:
            continue
        sim = metric(target_vec, vec)
        sims.append((sim, meta))
    sims.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, meta in sims[:limit]:
        entry = dict(meta)
        entry["similarity"] = sim
        results.append(entry)
    return results
