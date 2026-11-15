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

Test evidence: `docs/tdd/f0-f1.tdd.md` and `docs/tdd/f2-f3.tdd.md`.
