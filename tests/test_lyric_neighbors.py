import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from tools.lyric_neighbors import run_neighbors
from ma_lyrics_engine.schema import ensure_schema


def test_neighbors_returns_sorted_results(tmp_path):
    db_path = tmp_path / "neighbors.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    songs = [
        ("song_a", "A", "Artist1", 2020, [1, 0]),
        ("song_b", "B", "Artist2", 2021, [1, 0.1]),
        ("song_c", "C", "Artist3", 2022, [0, 1]),
    ]
    for sid, title, artist, year, vec in songs:
        conn.execute(
            "INSERT INTO songs (song_id, title, artist, year, peak_position, weeks_on_chart, source) VALUES (?, ?, ?, ?, NULL, NULL, 'test')",
            (sid, title, artist, year),
        )
        conn.execute("INSERT INTO features_song_vector (song_id, vector) VALUES (?, ?)", (sid, json.dumps(vec)))
    conn.commit()
    conn.close()

    out_path = tmp_path / "out.json"
    args = SimpleNamespace(db=str(db_path), song_id="song_a", limit=2, out=str(out_path), cmd=None, distance="cosine")
    logs = []
    run_neighbors(args, logs.append)
    data = json.loads(out_path.read_text())
    assert data["count"] == 2
    # song_b should be closer to song_a than song_c
    assert data["items"][0]["song_id"] == "song_b"
