# Capitalized implementation package (no lowercase dependency).
from .ttc import SegmentationResult, detect_ttc_stub, apply_ttc_gate_and_lift

__all__ = ["SegmentationResult", "detect_ttc_stub", "apply_ttc_gate_and_lift"]
