# Host inputs (compat notes)

The host consumes the same payload shape currently emitted as `.client.json` / `.client.rich.txt` from `tools/pack_writer.py -> build_client_helper_payload`.

Minimal expected fields:
- `region`, `profile`, `audio_name`
- `features_full` with at least: `tempo_bpm`, `duration_sec` (runtime), `loudness_LUFS`, `energy`, `danceability`, `valence`, `key`, `mode`
- `audio_axes` (0–1): `TempoFit`, `RuntimeFit`, `LoudnessFit`, `Energy`, `Danceability`, `Valence`
- HCI fields (host picks in order): `HCI_v1_final_score` → `HCI_v1_score` → `HCI_audio_v2.score`
- Optional `historical_echo_v1` (primary_decade, neighbor counts, top_neighbor with distance)
- Optional `advisor_target` (mode: `future_back` vs default)

Helper text format:
- Lines containing `/audio import { ... }` where `{...}` is JSON (host extracts the first JSON object after the marker).

Non-goal:
- Host never recomputes features or HCI; numbers are treated as ground truth.

Optional chat backend delegation:
- Keep the host as a thin IO/front door. Set `HOST_CHAT_BACKEND_MODE=on` (default `auto`) and include `client_rich_path` in chat requests (HTTP stub/FastAPI) to delegate replies to the modular `tools/chat` backend. If disabled or unavailable, host behavior is unchanged.
