import json
from ma_host.contracts import SONG_CONTEXT_KEYS, META_FIELDS, LYRIC_BUNDLE_KEYS, NEIGHBOR_FIELDS
from ma_host.song_context import build_song_context


def test_song_context_contract_minimal():
    meta = {"song_id": "s1", "title": "T", "artist": "A", "year": 2024}
    lyric_bundle = {"bridge": {"items": []}, "neighbors": {"items": []}}
    ctx = build_song_context(meta=meta, audio_bundle=None, lyric_bundle=lyric_bundle)
    assert SONG_CONTEXT_KEYS.issubset(ctx.keys())
    assert META_FIELDS.issubset(ctx["meta"].keys())


def test_lyric_neighbor_contract_fields():
    bundle = {
        "bridge": {"items": []},
        "neighbors": {"items": [{"song_id": "n1", "title": "x", "artist": "y", "year": 2020, "similarity": 0.9}]},
    }
    ctx = build_song_context(meta={"song_id": "s1"}, audio_bundle=None, lyric_bundle=bundle)
    items = ctx.get("lyrics", {}).get("neighbors", {}).get("items", [])
    if items:
        assert NEIGHBOR_FIELDS.issubset(items[0].keys())
