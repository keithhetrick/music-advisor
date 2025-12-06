from ma_lyric_engine.features import compute_features_for_song, load_vader
from ma_lyric_engine.utils import clean_lyrics_text


def test_family_theme_detects_grandma_tokens():
    text = """
    Wake up grandma, by your bedside we remember stories at the kitchen table.
    Grandfather and nana smiling in the photo album at home on the porch.
    """
    payload = compute_features_for_song(
        analyzer=None,
        concreteness_lex={},
        lyrics_id="lyr1",
        song_id="song1",
        clean_text=clean_lyrics_text(text),
        tempo_bpm=None,
        duration_ms=None,
    )
    theme_family = payload["features_song"].get("theme_family", 0.0)
    theme_nostalgia = payload["features_song"].get("theme_nostalgia", 0.0)
    assert theme_family > 0.0
    assert theme_nostalgia >= 0.0
