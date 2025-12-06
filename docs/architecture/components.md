# Advisor Host Components (Per-Concern Packages)

This repo exposes reusable, concern-specific packages you can drop into other projects:

- **auth/** — ID token verification + providers (`verify_google_id_token`, `AuthError`, `AuthContext`, `NoAuthProvider`, `StaticBearerAuthProvider`, `GoogleAuthProvider`). Optional signature verification via `PyJWT` (`auth_google_sig` extra).
- **session/** — Pluggable session stores (`InMemorySessionStore`, `FileSessionStore`, `RedisSessionStore`), converters, save/load helpers. Optional Redis via `session_redis` extra.
- **logging/** — Lightweight logging/metrics hooks (`log_event`, `record_metric`, `timing_ms`).
- **diagnostics/** — Redacted diagnostics exporter (`gather_diagnostics`).
- **adapter/** — Helper text/JSON parsing for `/audio import { ... }` (`parse_helper_text`, `parse_payload`).
- **schema/** — Reply shape validator (`validate_reply_shape`, `reply_schema.json`).
- **tutorials/** — Static tutorials/help content (`get_tutorial`, `tutorial_list`).
- **intents/** — Intent detection and quick_action allowlist (`detect_intent`, `sanitize_quick_actions`).

Usage: import directly from the package, e.g., `from advisor_host.auth import NoAuthProvider`, `from advisor_host.session import InMemorySessionStore`.

Optional deps/extras declared in `pyproject.toml`:

- `session_redis` → `redis>=5`
- `auth_google_sig` → `PyJWT>=2.8`
- `prometheus_client` (no extra tag) if you enable `HOST_PROM_ENABLED` for metrics export

Version: defined in `advisor_host/__init__.py` (`__version__`).

Each package has an explicit public API via `__all__`; host-specific code is not required to reuse them.

Lint/type configs: `.ruff.toml` and `mypy.ini` are provided for CI/static checks if you opt to enable them.
