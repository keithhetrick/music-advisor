"""
Utility wrappers for common path helpers.

These re-export `shared.config.paths` so downstream code can import from a
utilities namespace without reaching into config directly.
"""
from shared.config.paths import *  # noqa: F401,F403
