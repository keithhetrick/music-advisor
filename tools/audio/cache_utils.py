#!/usr/bin/env python3
"""Shim to shared FeatureCache implementation."""
from shared.ma_utils.cache_utils import FeatureCache  # noqa: F401

__all__ = ["FeatureCache"]

if __name__ == "__main__":
    cache = FeatureCache()
    print(cache.gc())
