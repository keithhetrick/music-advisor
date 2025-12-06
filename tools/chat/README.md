# Chat backend (tools/chat)

Headless, modular chat “brain” used by the thin host front door.

## Quick start

- Install (from repo root): `pip install -e src/ma_config -e shared -e tools/chat`
- Smoke (PYTHONPATH=.): `python - <<'PY'\nfrom tools.chat.chat_router import route_message\nfrom tools.chat.chat_context import ChatSession\nfrom pathlib import Path\nsess = ChatSession(session_id=\"demo\")\nreply = route_message(sess, \"tempo?\", client_path=Path(\"/abs/path/to/song.client.rich.txt\"))\nprint(reply)\nPY`
- Tests: if present under `tools/chat/tests`, run `PYTHONPATH=. pytest tools/chat/tests`

## Notes

- Intents/overlay dispatch live here; host remains a thin IO layer.
- Optional hooks: env `CHAT_PARAPHRASE_ENABLED` (paraphrase), `HOST_CHAT_BACKEND_MODE` (used by host) controls delegation.
