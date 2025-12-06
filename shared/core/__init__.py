"""
Shared core contracts (shim layer).

Keep core-level helpers here so engines/hosts can import from `shared.core.*`.
Currently re-exports profile helpers from shared.config.
"""

from shared.core.profiles import *  # noqa: F401,F403
