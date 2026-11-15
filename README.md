# Monitor de salud para astronautas

NASA Space Apps 2026. Prototipo de apoyo a la decisión. **No es un dispositivo médico.**

Plan de arquitectura: `docs/plan-arquitectura.md`.

## Desarrollo (Dev A)

```bash
uv sync                      # Python 3.12 y dependencias
docker compose -f docker/compose.yaml up -d --wait postgres   # PostgreSQL + pgvector (puerto 5433)
for m in platform monitoring telemetry; do uv run python -m spaceapp.platform.migrate $m; done   # migraciones
scripts/check.sh             # ruff, mypy, import-linter y pytest con cobertura (sin necesitar make)
uv run uvicorn --factory spaceapp.main:create_app             # API: /health y /ready
```

El puerto de la base se cambia con `SPACEAPP_DB_PORT`. El perfil, con `SPACEAPP_PROFILE`
(`dev1`, `dev2` o `jurado`, que es el valor por defecto). Las pruebas de integración usan
testcontainers y necesitan Docker en marcha.

Para ver el sistema funcionando con el simulador (el relay y el simulador están apagados por defecto):

```bash
SPACEAPP_RELAY_ENABLED=true SPACEAPP_SIMULATOR_AUTOSTART=true SPACEAPP_RULE_WINDOW_SCALE=0.0167 \
  uv run uvicorn --factory spaceapp.main:create_app
# tras ~2 min de datos normales, provoca una anomalía en el laboratorio:
curl -X POST localhost:8000/api/v1/sim/scenarios/co2_slow:start -H 'content-type: application/json' -d '{"zone":"lab"}'
```

`SPACEAPP_RULE_WINDOW_SCALE` acorta las ventanas de las reglas (1 h real) para la demostración. Con 1.0 se usan
los valores de la norma. Escenarios: `co2_slow`, `pressure_leak`, `humidity_high`, `o2_failure`, `heat`.

Evidencia de las pruebas: `docs/tdd/f0-f1.tdd.md` y `docs/tdd/f2-f3.tdd.md`.
