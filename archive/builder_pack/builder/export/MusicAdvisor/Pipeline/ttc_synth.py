# Pipeline/ttc_synth.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

@dataclass
class TTCInputs:
    # Raw candidates found in ingest/feats/pack/etc.
    ttc_real: Optional[float] = None                 # audio-derived TTC (best)
    ttc_lyrics: Optional[float] = None               # lyric-derived TTC (fallback)
    verse_span: Optional[Tuple[float, float]] = None # seconds
    chorus_span: Optional[Tuple[float, float]] = None

def synthesize_ttc_confidence(inp: TTCInputs) -> Dict[str, Any]:
    """
    Heuristic synthesizer for TTC confidence when upstream extractor doesn’t provide it.
    Rules (simple, explicit, auditable):
      - If audio-derived TTC exists -> conf = 0.80 (high)
      - Else if lyric-derived TTC exists -> conf = 0.50 (medium/unstable)
      - Else -> TTC=None, conf=None
    Spans pass through for lift attempt only when TTC is accepted later by the gate.
    """
    if inp.ttc_real is not None:
        return {
            "ttc_seconds": float(inp.ttc_real),
            "ttc_confidence": 0.80,
            "verse_span": inp.verse_span,
            "chorus_span": inp.chorus_span,
            "source": "audio"
        }
    if inp.ttc_lyrics is not None:
        return {
            "ttc_seconds": float(inp.ttc_lyrics),
            "ttc_confidence": 0.50,
            "verse_span": inp.verse_span,
            "chorus_span": inp.chorus_span,
            "source": "lyrics"
        }
    return {
        "ttc_seconds": None,
        "ttc_confidence": None,
        "verse_span": None,
        "chorus_span": None,
        "source": "none"
    }
