# Health monitor for astronauts

NASA Space Apps 2026. Decision-support prototype. **Not a medical device.**

Architecture plan: `docs/architecture-plan.md`.

## Development (Dev A)

```bash
uv sync                      # Python 3.12 and dependencies
docker compose -f docker/compose.yaml up -d --wait postgres   # PostgreSQL + pgvector (port 5433)
for m in platform monitoring telemetry; do uv run python -m spaceapp.platform.migrate $m; done   # migrations
scripts/check.sh             # ruff, mypy, import-linter and pytest with coverage (no make needed)
uv run uvicorn --factory spaceapp.main:create_app             # API: /health and /ready
```

The database port is changed with `SPACEAPP_DB_PORT`. The profile is set with `SPACEAPP_PROFILE`
(`dev1`, `dev2` or `jury`, which is the default). The integration tests use
testcontainers and need Docker running.

To see the system working with the simulator (the relay and the simulator are off by default):

```bash
SPACEAPP_RELAY_ENABLED=true SPACEAPP_SIMULATOR_AUTOSTART=true SPACEAPP_RULE_WINDOW_SCALE=0.0167 \
  uv run uvicorn --factory spaceapp.main:create_app
# after ~2 min of normal data, trigger an anomaly in the lab:
curl -X POST localhost:8000/api/v1/sim/scenarios/co2_slow:start -H 'content-type: application/json' -d '{"zone":"lab"}'
```

`SPACEAPP_RULE_WINDOW_SCALE` shortens the rule windows (1 h real) for the demo. With 1.0 the values from the
standard are used. Scenarios: `co2_slow`, `pressure_leak`, `humidity_high`, `o2_failure`, `heat`.

## Web console against the real backend

```bash
scripts/dev-backend.sh               # PostgreSQL (port 5434), migrations and the API on :8002 with the simulator
cd web && npm run dev:backend        # the console reads the API instead of the labeled demo data
```

`npm run dev:backend` uses `web/.env.backend` (`VITE_DATA_MODE=backend`). The browser only talks to the Vite
origin, which proxies `/graphql`, `/ws` and `/api` to `SPACEAPP_API_PROXY` (default `http://127.0.0.1:8002`) and
the assistant routes to `SPACEAPP_ASSISTANT_PROXY` (`:8000`, `python -m spaceapp.devtools.assistant_server`), so
CORS is not needed. Another API port: `SPACEAPP_API_PORT=8010 scripts/dev-backend.sh` and
`SPACEAPP_API_PROXY=http://127.0.0.1:8010 npm run dev:backend`. `npm run dev` keeps the demo mode.

### A mission in the database

```bash
SPACEAPP_DATABASE_URL=postgresql+asyncpg://spaceapp:spaceapp@localhost:5434/spaceapp \
  .venv/bin/python -m spaceapp.devtools.seed_mission --reset      # about 40 s
SPACEAPP_SIMULATOR_AUTOSTART=false scripts/dev-backend.sh          # keeps that state on screen
```

The seed replays three hours of simulated telemetry through the app's own use cases, so everything is
written by the modules and labeled as the running system would: the habitat map (from
`data/facility/plan.json`), readings of every zone, a slow CO₂ drift in the laboratory that the rules turn
into the `env-co2-1h` alert (with its recommendation, labeled DEMO), the incident that alert opens, a second
incident reported by hand and acknowledged, the day's tasks (one done, one blocked, one added by the crew)
and a Ground plan that went through the link and was confirmed. `--reset` empties the module tables first;
without it the seed refuses to run over existing readings. Run the API with the simulator on instead and it
keeps generating live readings, but the laboratory returns to nominal.

Not seeded because the backend has no storage for it yet: crew members, their wearable vitals and personal
sessions (the Crew health page keeps saying it awaits the crew service).

With the real backend, consent, baseline and "Sync now" are refused (`NOT_AVAILABLE`) until the backend has them,
and Ground templates show no zone or recurrence.

Test evidence: `docs/tdd/f0-f1.tdd.md` and `docs/tdd/f2-f3.tdd.md`.
