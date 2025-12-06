# Pipeline/extractor_adapter.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Iterable, List

from ma_hf_audiotools.Segmentation import SegmentationResult

@dataclass
class ExtractorBundle:
    """Normalized view of whatever the extractor (AudioTools) gives us."""
    audio_axes: List[float]                    # six floats in [0,1]
    ttc_seconds: Optional[float] = None
    ttc_confidence: Optional[float] = None     # may be None (we will synthesize)
    verse_span: Optional[Tuple[float,float]] = None
    chorus_span: Optional[Tuple[float,float]] = None
    extras: Dict[str, Any] = None

def _coerce_pair(x: Any) -> Optional[Tuple[float,float]]:
    try:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            return (float(x[0]), float(x[1]))
    except Exception:
        pass
    return None

def _coerce_axes(x: Any) -> List[float]:
    if not isinstance(x, (list, tuple)) or len(x) != 6:
        raise ValueError("audio_axes must be length-6 list/tuple")
    vals = [float(v) for v in x]
    if not all(0.0 <= v <= 1.0 for v in vals):
        raise ValueError("audio_axes must be in [0,1]")
    return vals

def adapt_extractor_payload(raw: Dict[str, Any]) -> ExtractorBundle:
    """
    Accepts lowercase keys typical of music-advisor and friends.
    Expected keys (tolerant): 'audio_axes', 'ttc_sec', 'ttc_conf', 'verse_span', 'chorus_span'.
    Extras are preserved for downstream advisory.
    """
    axes   = _coerce_axes(raw.get("audio_axes"))
    ttc_s  = raw.get("ttc_sec")
    ttc_c  = raw.get("ttc_conf")
    verse  = _coerce_pair(raw.get("verse_span"))
    chorus = _coerce_pair(raw.get("chorus_span"))
    extras = dict(raw)
    return ExtractorBundle(
        audio_axes=axes,
        ttc_seconds=float(ttc_s) if ttc_s is not None else None,
        ttc_confidence=float(ttc_c) if ttc_c is not None else None,
        verse_span=verse,
        chorus_span=chorus,
        extras=extras,
    )

def to_segmentation(bundle: ExtractorBundle) -> SegmentationResult:
    return SegmentationResult(
        ttc_seconds=bundle.ttc_seconds,
        ttc_confidence=bundle.ttc_confidence,
        verse_span=bundle.verse_span,
        chorus_span=bundle.chorus_span,
    )
