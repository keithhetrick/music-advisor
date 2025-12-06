# Plugins

Optional extension points live under `plugins/` (now located at `engines/audio_engine/plugins`; this shim keeps legacy imports working) and can be enabled via env or `config/plugins.json`.

Kinds:

- `logging`: structured logger factories (attr: `factory(prefix, defaults)`).
- `sidecar`: tempo/key sidecar runners (attr: `factory() -> callable(audio, out, **kwargs)`).
- `cache`: cache adapter factories (attr: `factory(cache_dir=None, backend=None)`).
- `exporter`: custom exporters (attr: `factory() -> callable(payload, path)`).

Enabling:

- Via env: `MA_LOGGING_PLUGIN=name`, `MA_SIDECAR_PLUGIN=name`, `MA_CACHE_PLUGIN=name`.
- Via config: add mappings in `config/plugins.json` (e.g., `"logging": {"json_printer": "plugins.logging.json_printer"}`).

Examples:

- `plugins/logging/json_printer.py`: emits structured JSON.
- `plugins/logging/http_post.py`: POSTs events; supports `endpoint`, `auth_token`, `auth_scheme`, `max_retries`, `backoff_base`, `backoff_max`, `timeout`, `headers`.
- `plugins/sidecar/stub.py`: stub tempo/key sidecar for tests/CI.
- `plugins/cache/memory_cache.py`: in-memory cache adapter for tests.

HTTP logger config example:

```json
{
  "logging": {
    "http_post": {
      "path": "plugins.logging.http_post",
      "defaults": {
        "endpoint": "https://logs.example.com/events",
        "auth_token": "YOUR_TOKEN",
        "auth_scheme": "Bearer",
        "timeout": 2.0,
        "max_retries": 4,
        "backoff_base": 0.25,
        "backoff_max": 2.5,
        "headers": {
          "X-App": "music-advisor"
        }
      }
    }
  }
}
```

Safety:

- Plugin load failures are isolated; callers fall back to defaults.
