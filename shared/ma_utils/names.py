"""
Central naming helpers for client-facing payloads.

We default the consumer token to "client" so filenames/flags stay consistent
across macOS and web frontends. A future override could read from env/flags,
but keeping a single source of truth here avoids scattered hard-coding.

Usage:
- Suffix/glob helpers for client artifacts: `client_txt_suffix()`, `client_json_suffix()`, `client_rich_suffix()`.
- Sidecar helpers: `tempo_sidecar_suffix()`, `tempo_sidecar_globs()`, placeholders for lyric sidecars.
- Override client token for experiments via env `MA_CLIENT_TOKEN`.

Notes:
- Pure helpers; no side effects. Keep naming aligned across tools/Automator/validators.
"""

import os
from typing import Iterable, List

# Default token; can be overridden via env for experiments.
CLIENT_TOKEN = os.getenv("MA_CLIENT_TOKEN", "client")


def client_txt_suffix() -> str:
    return f".{CLIENT_TOKEN}.txt"


def client_json_suffix() -> str:
    return f".{CLIENT_TOKEN}.json"


def client_rich_suffix() -> str:
    return f".{CLIENT_TOKEN}.rich.txt"


def client_txt_globs() -> List[str]:
    return [f"*{client_txt_suffix()}"]


def client_json_globs() -> List[str]:
    return [f"*{client_json_suffix()}"]


def client_rich_globs() -> List[str]:
    return [f"*{client_rich_suffix()}"]


# Legacy tokens removed; keep empty iterable for interface stability.
LEGACY_TOKENS: Iterable[str] = tuple()


def legacy_txt_globs() -> List[str]:
    return [f"*.{tok}.txt" for tok in LEGACY_TOKENS]


def legacy_json_globs() -> List[str]:
    return [f"*.{tok}.json" for tok in LEGACY_TOKENS]


def legacy_rich_globs() -> List[str]:
    return [f"*.{tok}.rich.txt" for tok in LEGACY_TOKENS]


def client_header_label() -> str:
    return CLIENT_TOKEN.upper()


# Sidecar artifact helpers (keeps filenames/globs centralized)
def tempo_sidecar_suffix() -> str:
    return ".sidecar.json"


def tempo_sidecar_globs() -> List[str]:
    return [f"*{tempo_sidecar_suffix()}"]


# Placeholder for future lyric sidecar outputs to keep naming consistent.
def lyric_sidecar_suffix() -> str:
    return ".lyric.sidecar.json"


def lyric_sidecar_globs() -> List[str]:
    return [f"*{lyric_sidecar_suffix()}"]


def tempo_norms_sidecar_suffix() -> str:
    return ".tempo_norms.json"


def tempo_norms_sidecar_globs() -> List[str]:
    return [f"*{tempo_norms_sidecar_suffix()}"]


def key_norms_sidecar_suffix() -> str:
    return ".key_norms.json"


def key_norms_sidecar_globs() -> List[str]:
    return [f"*{key_norms_sidecar_suffix()}"]

__all__ = [
    "client_header_label",
    "client_json_globs",
    "client_json_suffix",
    "client_rich_globs",
    "client_rich_suffix",
    "client_txt_globs",
    "client_txt_suffix",
    "key_norms_sidecar_globs",
    "key_norms_sidecar_suffix",
    "legacy_json_globs",
    "legacy_rich_globs",
    "legacy_txt_globs",
    "lyric_sidecar_globs",
    "lyric_sidecar_suffix",
    "tempo_norms_sidecar_globs",
    "tempo_norms_sidecar_suffix",
    "tempo_sidecar_globs",
    "tempo_sidecar_suffix",
]
