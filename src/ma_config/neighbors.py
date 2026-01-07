"""
Compatibility wrapper: delegates to shared.config.neighbors (source of truth).
"""
from shared.config.neighbors import (
    DEFAULT_NEIGHBORS_LIMIT,
    DEFAULT_NEIGHBORS_DISTANCE,
    DEFAULT_NEIGHBORS_CONFIG_PATH,
    resolve_neighbors_config,
)

__all__ = [
    "DEFAULT_NEIGHBORS_LIMIT",
    "DEFAULT_NEIGHBORS_DISTANCE",
    "DEFAULT_NEIGHBORS_CONFIG_PATH",
    "resolve_neighbors_config",
]
