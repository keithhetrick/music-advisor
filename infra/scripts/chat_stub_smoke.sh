#!/usr/bin/env bash
set -euo pipefail

# Smoke test for dockerized chat stub + Redis.
# - Spins up compose stack
# - Posts sample analyze payload
# - Prints reply

ROOT=$(cd "$(dirname "$0")/../.." && pwd)

echo "[*] Bringing up docker chat stub stack..."
docker-compose -f "$ROOT/docker/docker-compose.chat-stub.yml" up -d --build

echo "[*] Waiting 2s for stub to start..."
sleep 2

echo "[*] Posting sample analyze (uses docs/samples/chat_analyze_sample.json)..."
curl -s -X POST http://localhost:8090/chat \
  -H "Content-Type: application/json" \
  --data-binary @"$ROOT/docs/samples/chat_analyze_sample.json" | jq .

echo "[*] Health check:"
curl -s http://localhost:8090/health | jq .

echo "[done]"
