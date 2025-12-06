#!/usr/bin/env python3
"""
aee_version.py

Single source of truth for AEE/HCI version and key policy constants
for the music-advisor repo.

This file **does not implement any scoring logic**.
It only exposes metadata that can be logged, shown on cards,
or used by higher-level services (e.g., a client/frontend layer).

Naming is aligned with:

- CIF v1.2 (Creative Intelligence Framework, draft)
- AEE — Audio Echo Engine (audio KPI domain)
- HEM — Historical Echo Model (inside AEE)
- HCI — Hit Confidence Index (public KPI)
- US_Pop_2025 profile as canonical lane for this repo
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CIF / Engine / KPI versions
# ---------------------------------------------------------------------------

#: CIF document version this repo aligns with (methods & governance level).
CIF_VERSION: str = "CIF_v1.2_draft"

#: Audio Echo Engine implementation version in this repo.
#: This covers feature extraction → axes → composite → HCI (audio-only path).
AEE_VERSION: str = "AEE_v1.0_audio_only"

#: Historical Echo Model version (inside the AEE).
HEM_VERSION: str = "HEM_v1.0"

#: Public KPI version (HCI) produced by this repo for audio-only runs.
HCI_VERSION: str = "HCI_v1.0_audio_only"

# ---------------------------------------------------------------------------
# Policy knobs (frozen for this implementation)
# ---------------------------------------------------------------------------

#: Canonical profile id (see CIF v1.2).
PROFILE_ID: str = "US_Pop_2025"

#: Canonical KPI lane: Radio US.
CANONICAL_LANE: str = "radio_us"

#: Advisory lanes (future Host-level recommendation context).
ADVISORY_LANES: tuple[str, ...] = ("radio_us", "spotify")

#: Fusion weight β in:
#:   HCI = β * min(EACM_audio, c_audio) + (1 - β) * min(EACM_lyric, c_lyric)
#: Today (this repo): β = 1.0 → audio-only KPI.
BETA_AUDIO_VS_LYRIC: float = 1.0

#: Caps for engine composites, as per CIF v1.2.
AUDIO_CAP: float = 0.58
LYRIC_CAP: float = 0.58  # Reserved for LEE once implemented.

#: Seeds recommended in CIF v1.2 for reproducible runs (not yet widely used in code).
SEEDS: tuple[int, int, int] = (42, 314, 2718)

# ---------------------------------------------------------------------------
# Helper accessors
# ---------------------------------------------------------------------------

def summary_dict() -> dict:
    """
    Return a compact dictionary of the current AEE/HCI metadata.

    This can be embedded in:
    - Run cards
    - Calibration JSON
    - Debug logs
    - Client prompts (so the UI knows which engine it is talking to)
    """
    return {
        "cif_version": CIF_VERSION,
        "aee_version": AEE_VERSION,
        "hem_version": HEM_VERSION,
        "hci_version": HCI_VERSION,
        "profile_id": PROFILE_ID,
        "canonical_lane": CANONICAL_LANE,
        "advisory_lanes": list(ADVISORY_LANES),
        "beta_audio_vs_lyric": BETA_AUDIO_VS_LYRIC,
        "audio_cap": AUDIO_CAP,
        "lyric_cap": LYRIC_CAP,
        "seeds": list(SEEDS),
    }


if __name__ == "__main__":
    # Tiny CLI helper: print the freeze state.
    import json
    print(json.dumps(summary_dict(), indent=2, sort_keys=True))
