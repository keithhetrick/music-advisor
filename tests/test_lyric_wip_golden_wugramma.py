import json
from pathlib import Path

from tools.lyric_wip_report import render_report
from ma_lyrics_engine.bundle import build_bundle


def test_golden_wip_wugramma_fixture(tmp_path):
    fixture_dir = Path("tests/fixtures/lyric_wip_wugramma")
    bridge = json.loads((fixture_dir / "wip_bridge.json").read_text())
    neighbors = json.loads((fixture_dir / "wip_neighbors.json").read_text())
    report = render_report(bridge, neighbors, top_k=3, norms=None, include_self=False)
    assert "Wake up Grandma" in report
    bundle = build_bundle(bridge, neighbors)
    lci = bundle.get("lci", {})
    axes = lci.get("axes", {})
    assert 0 <= axes.get("structure_fit", 0) <= 1
    assert lci.get("score") is not None
    ttc = bundle.get("ttc", {})
    assert "ttc_confidence" in ttc
