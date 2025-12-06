"""
Contract constants for bundles and song_context structures.

Centralizing keys makes refactors/monorepo moves safer and keeps producers/consumers aligned.
"""

# Song context sections (mirrors build_song_context output)
SONG_CONTEXT_KEYS = {"meta", "audio", "lyrics"}

META_FIELDS = {"song_id", "title", "artist", "year"}

# Lyric bundle components (bridge + neighbors)
LYRIC_BUNDLE_KEYS = {"bridge", "neighbors"}

# Neighbor entry fields (subset used in tests/payloads)
NEIGHBOR_FIELDS = {
    "song_id",
    "title",
    "artist",
    "year",
    "similarity",
}
