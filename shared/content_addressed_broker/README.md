# content-addressed-broker

Content-addressed, immutable artifact delivery with a tiny HTTP broker and an in-process queue. It serves artifacts and manifests from a CAS layout with ETags, writes an index pointer per track, and delegates the actual computation to a pluggable runner.

## Features

- Submit/status endpoints: `POST /echo/jobs`, `GET /echo/jobs/{job_id}`
- Immutable artifact/manifest serving with ETags and cache headers: `/echo/{config_hash}/{source_hash}/{artifact_name}`
- Latest pointer per track: `/echo/index/{track_id}.json`
- Pluggable runner (dotted path, default: `tools.hci.historical_echo_runner:run`)
- Minimal deps; runs with the standard library.

## Quick start

```bash
pip install -e shared/content_addressed_broker

content-addressed-broker \
  --cas-root data/echo_cas \
  --runner tools.hci.historical_echo_runner:run \
  --artifact-name historical_echo.json \
  --manifest-name manifest.json \
  --port 8099
```

Submit a job:

```bash
curl -X POST http://127.0.0.1:8099/echo/jobs \
  -H "Content-Type: application/json" \
  -d '{"features_path":"/tmp/echo_run/foo.features.json","track_id":"foo"}'
```

Check status:

```bash
curl http://127.0.0.1:8099/echo/jobs/<job_id>
```

Fetch the latest artifact for a track:

```bash
curl http://127.0.0.1:8099/echo/index/foo.json
```

## Runner contract

- The runner callable must accept `features_path`, `out_root`, `track_id`, `run_id`, `config_hash`, `db_path`, `db_hash`, `probe_kwargs`, and any extra `runner_kwargs`.
- It must return a dict containing `artifact` and `manifest` (paths on disk). By default, the CAS layout is `/echo/{config_hash}/{source_hash}/`.
- The manifest is expected to include `artifact.sha256` and optionally `artifact.etag`.

## TaskConductor fit

- The broker/queue pair follows the TaskConductor pattern (submit → queue → worker → status → artifact).
- Swap the runner to reuse this broker for any job type.

## Configuration knobs

- `--runner`: dotted path to the runner callable.
- `--artifact-name` / `--manifest-name`: filenames to serve and validate.
- `--cas-root`, `--host`, `--port`: service location.

## Notes

- Defaults remain compatible with the Historical Echo runner (historical_echo.json + manifest.json in `data/echo_cas`).
- To generalize further, swap the runner and adjust filenames; the HTTP surface and CAS/ETag semantics stay the same.

## Release checklist (suggested)

- Bump version in `pyproject.toml`.
- Run `python -m pytest shared/content_addressed_broker/tests`.
- If publishing, build artifacts: `python -m build` from this folder.
- Verify CLI: `content-addressed-broker --help`.

## Logging

- Uses the standard library `logging`. The CLI sets a basic INFO handler if none exists. When embedding, configure logging in your host app or pass a logger into `EchoJobQueue` for custom routing.

## Testing

- Pytest examples live in `tests/` (success path, validation failure, HTTP contract). Run:

  ```bash
  python -m pytest shared/content_addressed_broker/tests
  ```

- For HTTP contract tests, we spin the server in-thread and assert submit/status/index/artifact flows; see `tests/test_http_contract.py`.

## Architecture (mermaid)

```mermaid
flowchart LR
  A[Client] -->|POST /echo/jobs| B[Broker]
  B --> C[Queue]
  C --> D[Runner (pluggable)]
  D --> E[CAS: /echo/{config}/{source}/artifact]
  E -->|manifest/etag| F[Index pointer /echo/index/{track_id}.json]
  A -->|GET jobs/id| B
  A -->|GET artifact/manifest| E
  A -->|GET index| F
```
