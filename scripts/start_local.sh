#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

if [[ -f "$BASE_DIR/.env" ]]; then
  set -a
  source "$BASE_DIR/.env"
  set +a
fi

MCP_PORT="${MCP_PORT:-18081}"
UI_PORT="${UI_PORT:-18000}"

mkdir -p "$BASE_DIR/.adk"

# 1. Start the local BACEN MCP server
PORT="$MCP_PORT" PYTHONPATH="$BASE_DIR/mcp_bacen" "$BASE_DIR/.venv/bin/uvicorn" src.main:app --host 127.0.0.1 --port "$MCP_PORT" &
MCP_PID=$!
trap "kill $MCP_PID 2>/dev/null || true" EXIT

for i in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:${MCP_PORT}/healthz" >/dev/null 2>&1; then
    echo "Local BACEN MCP server ready on http://127.0.0.1:${MCP_PORT}/mcp"
    break
  fi
  sleep 0.5
done

# 2. Start unified ADK + Executive End-User Web UI (/app)
exec "$BASE_DIR/.venv/bin/python3" "$BASE_DIR/.ui/serve_with_ui.py"
