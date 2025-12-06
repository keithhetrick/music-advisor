import sqlite3

from ma_lyrics_engine.lanes import assign_lane, era_bucket, tier_from_rank
from ma_lyrics_engine.ingest import upsert_song
from ma_lyrics_engine.schema import ensure_schema


def test_tier_assignment_from_rank():
    assert tier_from_rank(10) == 1
    assert tier_from_rank(80) == 2
    assert tier_from_rank(150) == 3
    assert tier_from_rank(250) is None


def test_era_bucket():
    assert era_bucket(1990) == "1985_1994"
    assert era_bucket(2000) == "1995_2004"
    assert era_bucket(2010) == "2005_2014"
    assert era_bucket(2020) == "2015_2024"
    assert era_bucket(1970) == "misc"
    assert era_bucket(None) is None


def test_upsert_song_sets_lane(tmp_path):
    db_path = tmp_path / "lane.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    upsert_song(conn, "song_lane", "Title", "Artist", 2010, 35, None, "kaggle_year_end")
    cur = conn.execute("SELECT tier, era_bucket FROM songs WHERE song_id=?", ("song_lane",))
    tier, era = cur.fetchone()
    assert tier == 1
    assert era == "2005_2014"
    # wip song with only year
    upsert_song(conn, "song_wip", "WIP", "Me", 2023, None, None, "wip_stt")
    cur = conn.execute("SELECT tier, era_bucket FROM songs WHERE song_id=?", ("song_wip",))
    tier, era = cur.fetchone()
    assert tier is None
    assert era == "2015_2024"
    conn.close()
