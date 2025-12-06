from tools.ma_calibrate import _slugify_family, _canonical_family_from_path
from pathlib import Path

def test_slug_variants():
    assert _slugify_family("08_indie_singerwriter") == "08_indie_singer_songwriter"
    assert _slugify_family("08-indie-singer-writer") == "08_indie_singer_writer"  # generic normalize
    # Canonical mapping hits FAMILY_SYNONYMS:
    p = Path("calibration/audio/08_indie_singerwriter/some/thing/pack.json")
    assert _canonical_family_from_path(p).endswith("08_indie_singer_songwriter")
