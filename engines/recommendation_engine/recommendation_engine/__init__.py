"""Recommendation/optimization engine package.

Exports compute_recommendation for convenience.
"""
from recommendation_engine.engine.recommendation import (
    classify_hci_band,
    compute_recommendation,
)

__all__ = ["compute_recommendation", "classify_hci_band"]
