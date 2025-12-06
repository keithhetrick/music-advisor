from types import SimpleNamespace

from ma_config.neighbors import resolve_neighbors_config


def test_resolve_neighbors_prefers_cli(monkeypatch):
    monkeypatch.setenv("LYRIC_NEIGHBORS_LIMIT", "9")
    monkeypatch.setenv("LYRIC_NEIGHBORS_DISTANCE", "euclidean")
    limit, dist = resolve_neighbors_config(cli_limit=3, cli_distance="cosine")
    assert limit == 3
    assert dist == "cosine"


def test_resolve_neighbors_env_when_cli_missing(monkeypatch):
    monkeypatch.setenv("LYRIC_NEIGHBORS_LIMIT", "7")
    monkeypatch.setenv("LYRIC_NEIGHBORS_DISTANCE", "euclidean")
    limit, dist = resolve_neighbors_config(cli_limit=None, cli_distance=None)
    assert limit == 7
    assert dist == "euclidean"


def test_resolve_neighbors_uses_config(monkeypatch, tmp_path):
    monkeypatch.delenv("LYRIC_NEIGHBORS_LIMIT", raising=False)
    monkeypatch.delenv("LYRIC_NEIGHBORS_DISTANCE", raising=False)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"limit": 11, "distance": "euclidean"}', encoding="utf-8")
    limit, dist = resolve_neighbors_config(cli_limit=None, cli_distance=None, cli_config=str(cfg))
    assert limit == 11
    assert dist == "euclidean"
