#!/usr/bin/env bash
# Starts the backend the web console reads in `npm run dev:backend` (web/.env.backend):
# PostgreSQL in Docker, all module migrations, and the API with the relay and the simulator on.
#
#   scripts/dev-backend.sh
#   cd web && npm run dev:backend        # http://localhost:5173, proxies to the API below
#
# Defaults avoid 5433 (often taken by another project's database) and match web/.env.backend.
# Override any of them from the shell: SPACEAPP_API_PORT, SPACEAPP_DB_PORT, SPACEAPP_PROFILE...
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${SPACEAPP_API_PORT:-8002}"
export SPACEAPP_DB_PORT="${SPACEAPP_DB_PORT:-5434}"
export SPACEAPP_DATABASE_URL="${SPACEAPP_DATABASE_URL:-postgresql+asyncpg://spaceapp:spaceapp@localhost:${SPACEAPP_DB_PORT}/spaceapp}"
export SPACEAPP_RELAY_ENABLED="${SPACEAPP_RELAY_ENABLED:-true}"
export SPACEAPP_SIMULATOR_AUTOSTART="${SPACEAPP_SIMULATOR_AUTOSTART:-true}"
# 1 h rule windows last about a minute, so an anomaly raises an alert in the demo.
export SPACEAPP_RULE_WINDOW_SCALE="${SPACEAPP_RULE_WINDOW_SCALE:-0.0167}"

if command -v uv >/dev/null 2>&1; then
  PY=(uv run python)
else
  PY=(.venv/bin/python)
fi

docker compose -f docker/compose.yaml up -d --wait postgres
for module in platform monitoring telemetry facility engagement groundlink crew; do
  "${PY[@]}" -m spaceapp.platform.migrate "$module"
done

echo "API on http://127.0.0.1:${PORT}  (GraphQL /graphql, WebSocket /ws, health /health)"
echo "Trigger an anomaly: curl -X POST localhost:${PORT}/api/v1/sim/scenarios/co2_slow:start -H 'content-type: application/json' -d '{\"zone\":\"lab\"}'"
exec "${PY[@]}" -m uvicorn --factory spaceapp.main:create_app --host 127.0.0.1 --port "$PORT"
