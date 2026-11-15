# Tareas de Dev A · núcleo y tiempo real

> NASA Space Apps 2026 · monitor de salud para astronautas
> Documento de trabajo para **Dev A**. Deriva de [`plan-arquitectura.md`](plan-arquitectura.md) (secciones 5 a 8, 10, 13 y 16) y de [`spaceapps-health-monitor-context.md`](spaceapps-health-monitor-context.md). Es el equivalente de [`tareas-dev-b.md`](tareas-dev-b.md).
> Historial y estado: [`bitacora.md`](bitacora.md). Evidencia de las pruebas ya hechas: [`tdd/f0-f1.tdd.md`](tdd/f0-f1.tdd.md).
> Las horas son de trabajo por persona, no de reloj.

---

## 0. Resumen

| | |
| --- | --- |
| **Rol** | Dueño de la plataforma (outbox y relay), telemetría, monitoreo y reglas, nave e incidencias, tripulación, misiones y tareas, enlace con Tierra y el gateway GraphQL y WebSocket |
| **Horas** | 31 h en total. 21,5 h en el corte P0 y 9,5 h en P1 y P2 |
| **Hecho** | **F0, F1, F2 y F3** (11 h). 293 pruebas, 97,53 % de cobertura (ver sección 3.4) |
| **Por hacer** | F4, F5, F9, F10, F11 y F15 (20 h) |
| **Lenguaje** | Python 3.12 con FastAPI, SQLAlchemy 2 asíncrono, PostgreSQL 16 con pgvector, Strawberry (GraphQL, aún por añadir) |
| **Compañero** | Dev B: toda la SPA y los módulos `knowledge` y `assistant` (todo el RAG) |
| **Regla de oro** | Los contratos se congelan primero. B trabaja sobre mocks hasta que A los vuelve reales |

### Línea de tiempo de Dev A

| Horas | Fase | Nombre | Prioridad | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 0 a 1 | F0 | Cimientos (conjunta con B) | P0 | 1 h | **Hecha** |
| 1 a 4 | F1 | Bus de eventos con outbox | P0 | 3 h | **Hecha** |
| 4 a 8 | F2 | Monitoreo y catálogo de reglas | P0 | 4 h | **Hecha** |
| 8 a 11 | F3 | Telemetría y simulador por zona | P0 | 3 h | **Hecha** |
| 11 a 16 | F4 | Nave, zonas e incidencias (backend) | P0 | 5 h | Pendiente |
| 16 a 20 | F5 | GraphQL y WebSocket | P0 | 4 h | Pendiente |
| 20 a 21 | | Holgura (A espera a B para la entrega) | | 1 h | |
| 21 a 22,5 | F9 | Entrega para el jurado (conjunta) | P0 | 1,5 h | Pendiente |
| 22,5 a 25 | F10 | Tareas: backend | P1 | 2,5 h | Pendiente |
| 25 a 29 | F11 | Plan desde Tierra: backend | P1 | 4 h | Pendiente |
| 29 a 32 | F15 | Enlace hacia Tierra y consentimiento | P2 | 3 h | Pendiente |

**La holgura de 1 h** sirve para pruebas de integración con B y para revisar contratos. No se asigna a más trabajo.

### Hitos en los que A interviene

| Hito | Hora | Qué entrega A | Estado |
| --- | --- | --- | --- |
| I0 · Contratos congelados | 1 | `contracts.py` de cada módulo, `event_registry.py`, bus en memoria | **Listo para revisión de B** |
| I1 · Outbox real | 4 | Outbox, relay e inbox | **Disponible** |
| I2 · Lecturas y simulador en vivo | 11 | El simulador emite lecturas por zona. B conecta los ticks WebSocket | **Simulador listo.** Los ticks por WebSocket dependen del gateway (F5), así que B usa sus grabaciones hasta I5 |
| I3 · Incidencias en vivo | 16 | Tickets, zonas y catálogo de tipos. B conecta el panel de la nave | Pendiente |
| I5 · GraphQL y WebSocket completos | 20 | B retira todos los mocks. Primera prueba de extremo a extremo | Pendiente |
| I6 · Entrega para el jurado | 22,5 | Imagen de Docker probada sin internet | Pendiente |
| I7 · P1 completo | 32 | Plan desde Tierra de punta a punta | Pendiente |

(I4, alerta con recomendación citada, depende de F8 de B.)

**Inconsistencia detectada en el plan:** el hito I2 pide conectar los ticks por WebSocket, pero el gateway es la fase F5 (hora 20). Hasta entonces B sigue con sus grabaciones de mensajes y I2 se cumple solo en la parte del simulador.

---

## 1. Alcance

### 1.1 Qué es de A

| Módulo | Qué hace | Tablas |
| --- | --- | --- |
| `platform` | Outbox, relay, inbox, `UnitOfWork`, perfiles, configuración, `/health` y `/ready` | `outbox_event`, `inbox_processed` |
| `telemetry` | Lecturas de cuerpo, zonas y radiación; rollup por minuto; simulador con escenarios | `sensor`, `reading`, `reading_rollup_1m`, `scenario_run` |
| `monitoring` | Catálogo de reglas, PIO₂, ventanas, anomalías de tendencia, ciclo de vida de la alerta | `rule`, `alert`, `alert_ack` |
| `facility` | Hábitat y plano de zonas, tickets de incidencia, catálogo de 61 tipos, estado de color de cada zona | `habitat`, `zone`, `incident_type`, `incident`, `incident_update` |
| `crew` | Perfiles, línea base y consentimientos | `crew_member`, `baseline`, `consent` |
| `engagement` | Plantillas y tareas con origen, tareas propias, recordatorios, rachas y logros | `task_template`, `task`, `reminder`, `achievement`, `crew_achievement` |
| `groundlink` | Enlace en las dos direcciones: cola hacia Tierra y plan desde Tierra | `link_state`, `outbound_batch`, `outbound_item`, `inbound_plan`, `ground_plan`, `ground_template` |
| `realtime` | Gateway WebSocket. No tiene tablas | |

### 1.2 Qué no es de A

- Los módulos `knowledge` y `assistant` y todo el RAG (Ollama, Whisper, Alexa): son de B.
- Toda la SPA (`web/`): es de B.
- Los resolvers GraphQL de Conocimiento y Asistente: los escribe B. **A compone el esquema y los registra.**

### 1.3 Reglas del proyecto que A debe respetar

1. **El motor de reglas es determinista y auditable.** El modelo de lenguaje nunca decide una alerta.
2. **El oxígeno se evalúa como presión parcial**, no como porcentaje: `PIO₂ = (P_total − 47 mmHg) × FO₂`. Lo mismo vale para el CO₂.
3. **Toda cifra sin fuente verificada se rotula `DEMO`.** Las bandas amarillas son propuesta del equipo y también.
4. **Los datos del cuerpo y del simulador llevan `origin = SIMULATED`** hasta la interfaz.
5. **Un solo dueño por módulo.** Un módulo solo importa de otro su `contracts` y su `facade`. Lo hace cumplir `import-linter`.
6. **Un esquema de PostgreSQL por módulo y sin claves foráneas entre esquemas.**
7. **Un cambio de estado y su evento se escriben en la misma transacción** (`UnitOfWork`). Nadie publica desde fuera de ella.
8. **Los handlers son idempotentes** por `(consumidor, event_id)`.
9. **La alerta nunca espera a un modelo de lenguaje.**
10. **El sistema funciona sin internet y sin enlace con Tierra.**
11. **No se hacen commits** salvo que el usuario los pida.

---

## 2. Cómo trabaja A

### 2.1 TDD en cada fase

Para toda fase: escribir la prueba, **verla fallar por la razón correcta** (RED), escribir el código mínimo, verla pasar (GREEN), refactorizar y comprobar la cobertura (mínimo 80 %). Cada bloque cierra con un informe de evidencia en `docs/tdd/`.

### 2.2 Qué ya existe en el repositorio

| Ruta | Contenido |
| --- | --- |
| `src/spaceapp/platform/events.py` | `EventEnvelope`, `EventPayload` |
| `src/spaceapp/platform/bus.py` | `EventBus`, `EventPublisher`, `HandlerContext`, `SubscriptionRegistry`, `InMemoryEventBus` |
| `src/spaceapp/platform/outbox/` | `UnitOfWork`, `add_to_outbox`, `OutboxRelay`, `backoff_seconds`, `outbox_stats` |
| `src/spaceapp/platform/{profiles,config,db,vocab,migrate}.py` | Perfiles, configuración, base de datos, vocabulario compartido, migraciones |
| `src/spaceapp/modules/*/contracts.py` | Los 22 eventos |
| `src/spaceapp/event_registry.py` | Registro de eventos |
| `src/spaceapp/main.py` | `create_app` con `/health` y `/ready` |
| `migrations/platform/` | Migración del outbox y el inbox |
| `tests/` | 293 pruebas (unitarias, de contrato, de arquitectura, de integración y extremo a extremo) |
| `docker/compose.yaml` | PostgreSQL con pgvector en el puerto 5433 |
| `scripts/check.sh` | ruff, mypy, import-linter y pytest con cobertura |
| `tools/docgen/` | Generador del plan y del artefacto |
| `src/spaceapp/modules/monitoring/` | Dominio (unidades, PIO₂, series, tendencia, reglas, motor, ciclo de vida), catálogo JSON, repositorio SQL y en memoria, handler de lecturas, reconocer alerta, fachadas `RuleQuery` y `ActiveAlertsQuery`, `GET /api/v1/rules/catalog.json` |
| `src/spaceapp/modules/telemetry/` | Lecturas y sensores, simulador con escenarios, ingesta idempotente, rollup por minuto, fachada `SqlReadingQuery`, R1 y R4 |
| `src/spaceapp/platform/ids.py` | Identificadores estables de hábitat, zona y sensor |
| `rules/catalog/monitoring.json` | Catálogo de 25 reglas con fuente y estado de evidencia |
| `data/telemetry/sim_layout.json` | Las 10 zonas simuladas |
| `migrations/{monitoring,telemetry}/` | Migraciones propias de cada esquema |

### 2.3 Cómo se escribe un handler

Un handler recibe `(evento, HandlerContext)`. Se escribe **una vez** y corre igual sobre el bus en memoria (`ctx.session` es `None`) y sobre el outbox real (`ctx.session` es la transacción del handler). Para publicar un evento derivado se usa `ctx.publish(...)`: con el outbox real queda en la misma transacción y se descarta si el handler falla.

```python
async def on_readings_recorded(event: EventEnvelope, ctx: HandlerContext) -> None:
    payload = event.payload_as(ReadingsRecorded)
    ...  # lógica del caso de uso
    await ctx.publish(EventEnvelope.from_payload(AlertRaised(...), ...))
```

### 2.4 Estructura de un módulo

```text
src/spaceapp/modules/<modulo>/
  domain/            # reglas y agregados. Sin FastAPI, SQLAlchemy ni Strawberry
  application/       # casos de uso y handlers
  ports/             # interfaces de entrada y salida
  adapters/
    inbound/         # rest.py, graphql.py, events.py
    outbound/        # sql.py y los adaptadores de cada puerto
  contracts.py       # eventos públicos. Lo único que otros módulos importan
  facade.py          # consultas de solo lectura expuestas a otros módulos
migrations/<modulo>/ # Alembic propio y tabla de versión propia
```

Capas permitidas: `adapters` > `application` > `ports` > `domain`.

### 2.5 Comandos

```bash
scripts/check.sh                                              # ruff, mypy, import-linter, pytest + cobertura
docker compose -f docker/compose.yaml up -d --wait postgres   # base local (puerto 5433)
uv run python -m spaceapp.platform.migrate <modulo>           # aplica migraciones
uv run uvicorn --factory spaceapp.main:create_app             # API
```

Las pruebas de integración necesitan Docker en marcha (`systemctl --user start docker-desktop`).

### 2.6 Convenciones

- **Ramas:** `a/<fase>-<tema>`, de menos de 2 h.
- **Contratos:** un cambio en `contracts.py`, en el esquema GraphQL o en los mensajes WebSocket exige revisión de B **antes** de implementarlo.
- **`CODEOWNERS`:** hay que sustituir `@dev-a` y `@dev-b` por los usuarios reales.

---

## 3. Fases en detalle

### 3.1 F0 · Cimientos (conjunta con B) · 1 h · P0 · **HECHA**

**Objetivo:** dejar repositorio, contratos y herramientas listos para trabajar en paralelo.

- [x] **0.1 Proyecto y herramientas (0,25 h):** `uv`, Python 3.12, `pyproject.toml`, ruff, mypy estricto, pytest, import-linter.
- [x] **0.2 Estructura y contratos (0,25 h):** 9 módulos con su esqueleto hexagonal y los 22 eventos como modelos Pydantic con `extra="forbid"`.
- [x] **0.3 Sobre del evento y bus en memoria (0,25 h):** `EventEnvelope` con tipo `modulo.hecho` validado y `InMemoryEventBus` (idempotente, FIFO, errores aislados).
- [x] **0.4 Perfiles, composition root y reglas de arquitectura (0,25 h):** `dev1`, `dev2`, `jurado`; `create_app`; 4 contratos de import-linter con 4 canarios; `docker/compose.yaml`.

**Cumple:** I0. **Pendiente solo la revisión de B** (sección 8).

### 3.2 F1 · Bus de eventos con outbox · 3 h · P0 · **HECHA**

**Objetivo:** guardar estado y evento en una transacción y entregar cada evento al menos una vez, sin repetir trabajo.

- [x] **1.1 Migración (0,5 h):** `platform.outbox_event` (con `version`, `correlation_id` y `causation_id`), `platform.inbox_processed`, índice parcial de pendientes y restricción de estados.
- [x] **1.2 `UnitOfWork` y publicador (0,5 h):** estado y evento en la misma transacción. `NOTIFY` solo al confirmar.
- [x] **1.3 Relay (1,25 h):** `LISTEN/NOTIFY` con sondeo de respaldo, `FOR UPDATE SKIP LOCKED`, orden por id, backoff 1 a 60 s, paso a `dead` a los 8 intentos, un handler por transacción con su marca en el inbox, aislamiento entre consumidores.
- [x] **1.4 `/health` y `/ready` (0,25 h):** pendientes, muertos y retraso del evento más antiguo. 503 si la base no responde.
- [x] **1.5 Pruebas de integración (0,5 h):** atomicidad, duplicados, caída del relay, backoff, `dead`, orden, concurrencia.

**Cumple:** I1.

### 3.3 Diferencias respecto al plan original (ya aplicadas)

| Plan | Lo construido | Motivo |
| --- | --- | --- |
| Handler `async def h(event)` | `h(event, HandlerContext)` | Un solo handler corre en memoria y sobre el outbox, y puede publicar en la misma transacción |
| Tabla del outbox sin `version` ni correlación | Se añadieron `version`, `correlation_id`, `causation_id` | Están en el sobre del evento |
| Puerto de base de datos 5432 | 5433 (`SPACEAPP_DB_PORT`) | El 5432 lo usa otro proyecto del usuario |
| `make check` | `scripts/check.sh` | `make` no está instalado |
| Detector de tendencia con 65 puntos de historia | Ventanas y mínimos **por regla** (`params`) | Con la atmósfera muestreada cada 5 s (V2 6001) nunca habría 65 puntos. CO₂ y PIO₂ usan línea base de 120 a 30 s. Temperatura y humedad, que se muestrean cada minuto, usan 20 a 5 min |
| `env-dpdt` con ventana de 60 s | Ventana de 10 s | Una fuga real promedia unos 6 psi/min en 60 s y no llegaba a 13,5. En 10 s llega a ~16 |
| Escalada de severidad como evento | Reemplazo de reglas | Cada regla tiene una severidad fija: subir de nivel es resolver la alerta leve y levantar la grave. No hace falta `monitoring.alert_escalated` |
| Reglas con ventana de 1 h siempre activas | Exigen que los datos cubran al menos la mitad de la ventana | Evita que un pico en el arranque cuente como promedio de 1 h. El tiempo de demostración se acelera con `rule_window_scale`, sin inventar datos |
| Handler de `crew.baseline_updated` (2.5) y `BaselineQuery` (2.6) | **No se hicieron** | Aún no hay reglas relativas a la línea base (nivel 3) que los usen. Se hacen con ellas |
| Reloj del simulador | Aproximación exponencial exacta | El resultado no depende del tamaño del paso de tiempo |

### 3.4 Evidencia

293 pruebas pasan (122 del Bloque 1, 3 del generador de documentos y 168 del Bloque 2), cobertura 97,53 %, ruff y mypy estricto sin errores, 4 contratos de arquitectura cumplidos. Detalle en [`tdd/f0-f1.tdd.md`](tdd/f0-f1.tdd.md) y [`tdd/f2-f3.tdd.md`](tdd/f2-f3.tdd.md).

---

### 3.5 F2 · Monitoreo y catálogo de reglas · 4 h · P0 · **HECHA**

**Objetivo:** que cada lectura se evalúe de forma determinista contra un catálogo de reglas con fuente, y que el ciclo de vida de la alerta sea consistente.

**Depende de:** F1. **Habilita:** F3 (consume lecturas), F4 (consume alertas) y el hito I4 de B.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Consume | `telemetry.readings_recorded` (valores más recientes por sensor y zona), `crew.baseline_updated`. Lee `ReadingQuery` de Telemetría y `BaselineQuery` de Tripulación |
| Publica | `monitoring.alert_raised`, `monitoring.alert_acknowledged`, `monitoring.alert_resolved` |
| Expone | Fachadas `RuleQuery` (la usa Conocimiento, de B) y `ActiveAlertsQuery` (la usan Nave y Asistente). `GET /api/v1/rules/catalog.json` |

**Valores de las reglas (del documento de contexto, sección 5.2)**

| Regla | Valor | Requisito | Estado |
| --- | --- | --- | --- |
| `env-co2-1h` | ppCO₂ promedio de 1 h ≤ 3 mmHg. Pre-alerta desde 2,5. Sobre 4,5, fatiga y náuseas | V2 6004. TB-004 | `VERIFICADO`. La pre-alerta es `DEMO`. El valor de 4,5 es `TB` |
| `env-pio2` | Normoxia 145 a 155 mmHg. Rojo bajo 127. Crítico en 122 o menos (promedio de 1 h). Rojo sobre 356. Amarillo bajo 145 y sobre 155 | V2 6003, Tabla 6.2-1 | Límites `VERIFICADO`. Amarillos `DEMO` |
| `env-ptotal` | 34,5 < P ≤ 103 kPa | V2 6006 | `VERIFICADO` |
| `env-dpdt` | Cambio de presión ≤ 13,5 psi/min si supera 1,0 psi | V2 6007 | `VERIFICADO` |
| `env-n2` | Gas diluyente ≥ 30 % | V2 6002 | `VERIFICADO` |
| `env-rh`, `env-t` | Zona de desempeño 20 a 25 °C y 30 a 60 % HR. Límite de salud 18 a 27 °C y 25 a 75 % HR | V2 6012 y V2 6013 | Aproximación `DEMO` (el texto solo da los anclajes de la figura) |

Conversiones: 1 kPa = 7,50062 mmHg. 1 psi = 51,7149 mmHg.

**Tareas**

- [x] **2.1 Catálogo de reglas (0,75 h)**
  - JSON versionado en `rules/catalog/` con: `key`, `kind` (`umbral` o `tendencia`), `parameter`, `operator`, `threshold`, `unit`, `window_s`, `severity`, `source_requirement`, `source_document`, `evidence_state`, `hrp_hazard`, `action_key`, `active`.
  - Cargador con validación: una regla sin fuente o sin estado de evidencia no carga. Una regla `DEMO` se etiqueta como tal.
  - Migración de `monitoring.rule`, `alert` y `alert_ack` en `migrations/monitoring/`.
- [x] **2.2 Funciones puras de dominio (0,75 h)**
  - Conversiones de presión, `PIO₂ = (P − 47) × FO₂`, presión parcial de CO₂, ventanas móviles (promedio de 1 h) y velocidad de cambio de presión.
  - Sin E/S. Pruebas con Hypothesis (propiedades) además de los casos.
- [x] **2.3 Motor de evaluación por zona (1 h)**
  - `evaluate(lecturas, reglas)` devuelve los impactos con valor, banda, regla y evidencia. Evalúa cada zona por separado.
  - **Seis vectores de prueba obligatorios** (sección 6.2).
- [x] **2.4 Detector de anomalías de tendencia (0,5 h)**
  - Compara la media de los últimos 5 s con los 40 s previos (ventana de −60 a −20 s). Marca anomalía si el cambio supera el máximo entre 4σ y un mínimo por métrica: CO₂ 0,6 mmHg, humedad 6 %, temperatura 1,5 °C, PIO₂ 6 mmHg, presión 4 kPa.
  - Exige al menos 65 puntos de historia. Siempre `DEMO`. No dispara con ruido normal y sí con una deriva sostenida.
- [x] **2.5 Ciclo de vida de la alerta (0,5 h)** (sin el handler de `baseline_updated`: ver diferencias)
  - Estados `raised`, `acknowledged`, `resolved`. Deduplicación por `(regla, zona)` mientras siga activa (índice único parcial). Histéresis para que no parpadee.
  - Handler de `readings_recorded` y de `baseline_updated`. Publica por el outbox en la misma transacción.
  - Reconocer es idempotente.
- [x] **2.6 Fachadas (0,25 h):** `RuleQuery` y `ActiveAlertsQuery` en `facade.py`. `BaselineQuery` de Tripulación queda para cuando existan reglas relativas a la línea base.
- [x] **2.7 Exportar el catálogo (0,25 h):** `GET /api/v1/rules/catalog.json` con caché por versión.

**Criterios de aceptación**

- Los seis vectores de prueba dan el resultado esperado.
- La misma lectura evaluada dos veces no duplica la alerta.
- Una regla sin fuente o sin estado de evidencia no se carga.
- Cada alerta lleva regla, valor medido, documento, requisito y estado de evidencia.
- `import-linter` en verde.

**Cómo quedó (resumen):** el catálogo tiene 25 reglas (20 de umbral y 5 de tendencia). El motor evalúa por zona y es puro. Una regla más grave reemplaza a las leves (`supersedes`). El ciclo de vida usa histéresis de 3 evaluaciones. La alerta se guarda con su evidencia y el evento en la misma transacción. Reconocer es idempotente. Los 6 vectores de prueba dan lo esperado.

**Hito:** alimenta I2 (junto con F3) e I4 (con F8 de B).

---

### 3.6 F3 · Telemetría y simulador por zona · 3 h · P0 · **HECHA**

**Objetivo:** recibir lecturas por lote de forma idempotente y producir datos simulados realistas por zona.

**Depende de:** F1. **Habilita:** I2.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Publica | `telemetry.readings_recorded` (un evento por lote, con los últimos valores por sensor y zona), `telemetry.scenario_changed` |
| Expone | `POST /api/v1/telemetry/readings` (R1), `POST /api/v1/sim/scenarios/{key}:start · :stop` (R4). Fachada `ReadingQuery` |

**Frecuencias de muestreo de la norma (V2 6001, Tabla 6.1-1):** atmósfera cada 5 s, presión cada 1 s, temperatura y humedad cada 1 min.

**Tareas**

- [x] **3.1 Esquema `telemetry` (0,75 h):** `sensor` (con `zone_id` y `origin`), `reading` **particionada por día** con índice BRIN en `ts`, `reading_rollup_1m` y `scenario_run`. Migración propia.
- [x] **3.2 Ingesta por lotes (0,75 h):** R1 responde `202`. Idempotente por `(sensor_id, ts)`. Lotes de hasta 500 lecturas. Un solo `readings_recorded` por lote, nunca uno por lectura.
- [x] **3.3 Rollup y `ReadingQuery` (0,5 h):** el handler mantiene `reading_rollup_1m`. La fachada devuelve promedios en ventana (por ejemplo ppCO₂ de 1 h).
- [x] **3.4 Simulador con escenarios (0,75 h):** zonas con valores nominales (101,3 kPa, 21 % de O₂, CO₂ 0,4 a 1,1 mmHg, 21 a 24 °C, 36 a 52 % HR) con ruido. Escenarios: normal, CO₂ lento, fuga de presión, humedad alta, fallo de O₂, calor. Control por R4. Origen `SIMULATED`.
- [x] **3.5 Prueba de extremo a extremo (0,25 h):** escenario de CO₂ → `readings_recorded` → `alert_raised` en el outbox.

**Criterios de aceptación**

- Enviar dos veces el mismo lote deja las lecturas una sola vez.
- Todo dato del simulador lleva `origin = SIMULATED`.
- Un escenario de CO₂ lento produce primero la anomalía de tendencia y después la alerta por umbral.
- Con el simulador apagado, el sistema arranca igual.

**Cómo quedó (resumen):** 50 sensores simulados (5 por zona, con el periodo de muestreo de la norma). La ingesta usa `INSERT … ON CONFLICT DO NOTHING` y publica un solo evento por lote con los últimos valores. `reading` se particiona por día y las particiones se crean al ingerir. Los identificadores de zona y sensor son estables (`platform/ids.py`) para que Nave coincida sin importar a Telemetría. El relay y el simulador arrancan con la aplicación solo si se pide (`SPACEAPP_RELAY_ENABLED`, `SPACEAPP_SIMULATOR_AUTOSTART`).

**Prueba en vivo:** con el reloj real, 130 s normales dieron 1.930 lecturas y ninguna alerta. Al provocar el escenario de CO₂ en el laboratorio aparecieron la tendencia (Atención), la pre-alerta (Atención) y la alerta verificada (Alerta), las dos primeras resueltas por reemplazo. Solo se alteró esa zona, el outbox quedó vacío y no hubo errores.

**Hito:** I2 (hora 11), en la parte del simulador.

---

### 3.7 F4 · Nave, zonas e incidencias (backend) · 5 h · P0

**Objetivo:** que cada alerta por zona abra un ticket con tipo, descripción, severidad y ubicación, y que cada zona tenga su estado de color.

**Depende de:** F2 y F3. **Habilita:** I3 y el panel de la nave de B (F7).

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Consume | `monitoring.alert_raised`, `monitoring.alert_resolved`. Lee `ActiveAlertsQuery` de Monitoreo |
| Publica | `facility.incident_opened`, `incident_updated`, `incident_resolved`, `zone_status_changed` |
| GraphQL | `ship`, `incidents`, `incident`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |

**Tareas**

- [ ] **4.1 Esquema `facility` (0,75 h):** `habitat`, `zone` (con `layout` JSON y `status`), `incident_type`, `incident`, `incident_update`. Migración propia. Un ticket automático por zona activa (`source_alert_id` como referencia blanda).
- [ ] **4.2 Plano en JSON (0,5 h):** el plano de las 10 zonas (ingeniería, soporte vital, laboratorio, enfermería, puente, esclusa, almacén, gimnasio, cocina y dormitorios) como dato en `data/facility/`. **Cambiar de nave a base lunar es cambiar datos, no código.** Todo `DEMO`.
- [ ] **4.3 Catálogo de tipos de incidencia (0,75 h):** 61 tipos en 12 categorías como datos versionados (el catálogo está en `tools/docgen/data.py`). Cargador con validación. Prueba: toda clave de regla de un tipo `AUTO` existe en el catálogo de reglas, o está en una lista explícita de reglas pendientes.
- [ ] **4.4 Handlers de alerta (1,5 h)**
  - `alert_raised` con severidad Alerta o mayor abre un ticket automático por zona. La tendencia (severidad Atención) **no** abre ticket.
  - Un ticket abierto por zona: si llegan más alertas se actualiza su descripción y, si sube la severidad, se publica `incident_updated`.
  - `alert_resolved` marca «valores normales, puede cerrarse». **El ticket no se cierra solo.**
  - Un ticket automático no puede resolverse mientras haya alertas activas en su zona. Un ticket manual sí.
  - Reporte manual (`reportIncident`) por categoría y tipo, con severidad y acciones por defecto.
- [ ] **4.5 Estado de color de cada zona (0,5 h):** máximo entre las alertas activas y los tickets abiertos. Se recalcula al arrancar con `ActiveAlertsQuery`. Publica `zone_status_changed` solo si cambia.
- [ ] **4.6 GraphQL (1 h):** consultas y mutaciones con resultados tipados (`union` de éxito y errores, sin excepciones para errores esperados), paginación por cursor y DataLoaders.

**Criterios de aceptación**

- Un `alert_raised` de severidad Alerta en una zona abre exactamente un ticket y la zona pasa a rojo en la misma transacción.
- Una segunda alerta en la misma zona no abre otro ticket.
- Un ticket automático con valores fuera de rango no se puede resolver.
- Cambiar el JSON del plano cambia las zonas devueltas por `ship`.
- Reiniciar el servicio reconstruye el estado de las zonas.

**Hito:** I3 (hora 16).

---

### 3.8 F5 · GraphQL y WebSocket · 4 h · P0

**Objetivo:** que B consuma un esquema GraphQL y un canal WebSocket completos y estables.

**Depende de:** F4. **Habilita:** I5. **Añadir dependencia:** `strawberry-graphql[fastapi]`.

**Tareas**

- [ ] **5.1 Composición del esquema (1,5 h)**
  - Strawberry montado en FastAPI. Cada módulo aporta su fragmento (`graphql.py`) y A los compone en `interfaces/graphql/schema.py`. Los resolvers de B (Conocimiento y Asistente) se registran sin que A los escriba.
  - Consultas y mutaciones de A: `dashboard`, `readings`, `alerts`, `alert`, `rules`, `zoneReadings`, `crewMember`, `acknowledgeAlert`, `recordBaseline`, `setConsent`, y las de nave de F4.
  - Resultados tipados con `union`. Límite de profundidad y de costo. DataLoaders contra N+1.
- [ ] **5.2 Gateway `/ws` (1,5 h)**
  - Un endpoint con `subscribe` y `unsubscribe` por topic (`habitat`, `crew`, `alerts`, `assistant`).
  - Traduce los eventos del bus a los 14 mensajes del plan (tabla en la sección 5.3). `seq` es el `id` del outbox cuando el mensaje nace de un evento.
  - **`resume { after_outbox_id }`:** reenvía desde `outbox_event` (retención de 24 h).
  - `ping` y `pong` cada 15 s.
  - **Presión inversa:** cola de 500 mensajes por cliente. Se descartan primero los `telemetry.tick`. **Las alertas no se descartan.**
- [ ] **5.3 Ticks coalescidos (0,25 h):** `telemetry.tick` a 1 Hz como máximo por zona y sensor, a partir de `readings_recorded`.
- [ ] **5.4 Contratos publicados y operación (0,5 h):** exportar `schema.graphql`, el OpenAPI y `ws-messages.schema.json` para que B genere tipos y mocks. Ruta de reencolado `POST /api/v1/admin/outbox/{id}:replay` (R8) y `outboxStats` (solo perfiles de desarrollo). Limpieza de eventos `done` con más de 24 h.
- [ ] **5.5 Prueba de extremo a extremo (0,25 h):** escenario → alerta por WebSocket en menos de 1 s → reconocer por GraphQL.

**Criterios de aceptación**

- Un cliente que se cae y reanuda con `resume` recibe lo que se perdió, sin duplicados.
- Con la cola llena se descartan ticks y nunca alertas.
- `schema.graphql` y `ws-messages.schema.json` se regeneran sin cambios si el contrato no cambió.
- Un escenario de CO₂ llega a un cliente WebSocket en menos de 1 s (a medir, es una meta propuesta).

**Hito:** I5 (hora 20). B retira todos los mocks.

---

### 3.9 F9 · Entrega para el jurado (conjunta con B) · 1,5 h para A · P0

**Objetivo:** que el jurado ejecute todo con un comando y sin internet.

**Depende de:** F5, F7 y F8 (hora 21).

- [ ] **9.1 Dockerfile del backend (0,5 h):** imagen con Python 3.12, dependencias fijadas y usuario sin privilegios.
- [ ] **9.2 Compose completo (0,25 h):** aplicación y PostgreSQL con pgvector, con perfil `jurado` por defecto y variable de perfil visible.
- [ ] **9.3 Migraciones al arrancar (0,25 h):** se aplican las migraciones de cada módulo en orden y de forma idempotente.
- [ ] **9.4 Prueba en otra computadora (0,5 h, con B):** sin internet, sin GPU y con el micrófono bloqueado.

**Criterios de aceptación:** un solo comando levanta backend, base de datos y SPA con el perfil `jurado`. Sin Ollama, la recomendación de plantilla con cita sigue funcionando.

**Hito:** I6 (hora 22,5).

---

### 3.10 F10 · Tareas, backend · 2,5 h · P1

**Objetivo:** tareas diarias de salud, nave e incidentes con origen, y tareas propias de la tripulación.

**Depende de:** F9. **B construye la interfaz** sobre mocks hasta que A termine.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Consume | `monitoring.alert_raised · alert_acknowledged · alert_resolved`, `facility.incident_opened · incident_resolved`, `knowledge.recommendation_ready` (de B). Lee `ActionCatalogQuery` (de B) y `ZoneQuery` |
| Publica | `engagement.task_assigned`, `task_completed`, `task_created`, `task_blocked` |
| GraphQL | `tasks`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask`, `snoozeReminder` |

**Tareas**

- [ ] **10.1 Esquema (0,5 h):** `task_template`, `task` (con `kind`, `origin`, `template_id`, `blocked_reason`), `reminder`, `achievement`, `crew_achievement`.
- [ ] **10.2 Handlers (0,75 h):** las tareas de incidente nacen al abrirse un ticket y se completan al cerrarlo. Las medidas de una alerta nacen de la recomendación.
- [ ] **10.3 Tareas propias (0,75 h):** `TRIPULACION` puede crear, editar y borrar. **Una tarea de Tierra no se puede editar ni borrar:** devuelve un error tipado. Se puede completar, posponer o **bloquear con motivo** (no se borra).
- [ ] **10.4 GraphQL (0,5 h):** resolvers y errores tipados. Solo las rutinas de salud suman a la racha y a los logros. **Las alertas críticas no se gamifican.**

**Criterios de aceptación**

- Una tarea propia se crea sin enlace con Tierra.
- Una tarea de incidente se completa al resolver su ticket.
- Una tarea de Tierra rechaza editar o borrar con un error tipado.
- Registrar si una medida funcionó (`effective`) se publica en `task_completed`.

---

### 3.11 F11 · Plan desde Tierra, backend · 4 h · P1

**Objetivo:** que el centro de control programe tareas con planes versionados y la nave los aplique de forma idempotente, conservando el último plan si se corta el enlace (opción B).

**Depende de:** F9. **B construye** el panel del centro de control.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Entra | `POST /api/v1/groundlink/inbound/plans` (R9), idempotente por `batch_id` y `plan_version` |
| Publica | `groundlink.ground_plan_received`, `engagement.ground_plan_applied` |
| GraphQL (rol `ground`) | `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |
| Lee | `TaskStatusQuery` de Misiones, filtrada por consentimiento |

**Tareas**

- [ ] **11.1 Esquema (0,75 h):** `inbound_plan` (con `batch_id` y `plan_version` únicos, hash y estado), `ground_plan` y `ground_template` (lado de Tierra, solo en el despliegue de Tierra o en la demo).
- [ ] **11.2 Recepción (0,75 h):** R9 valida versión e integridad (hash). Versión menor o repetida: se ignora. Plan corrupto: se rechaza completo con motivo. Responde `202` y publica `ground_plan_received`.
- [ ] **11.3 Aplicación en Misiones (1,25 h):** una transacción. Crea, actualiza y cancela plantillas con origen `TIERRA`. Un ítem inválido (zona o asignado inexistentes) se rechaza solo él, con motivo, y el resto se aplica. Publica `ground_plan_applied` con lo aplicado y lo rechazado.
- [ ] **11.4 Lado de Tierra y enlace simulado (1 h):** GraphQL de borrador y publicación. Adaptador `GroundLink` simulado con demora y corte configurables.
- [ ] **11.5 Reglas de conflicto (0,25 h):** una prueba por cada una de las reglas de la sección 13.11 del plan.

**Reglas de conflicto (resumen)**

| Situación | Regla |
| --- | --- |
| Llega la v12 y la v11 ya se aplicó | Una transacción. Lo completado hoy no se toca. Los cambios rigen para instancias futuras |
| Versión menor o repetida | Se ignora (idempotente) |
| Plan corrupto | Se rechaza completo con motivo y se conserva el anterior |
| Un ítem inválido | Se rechaza solo ese ítem |
| Tierra cancela algo ya completado | Queda completado. La cancelación rige para el futuro |
| La tripulación no puede cumplir una tarea de Tierra | Se bloquea con motivo y no se borra |
| Se corta el enlace | Sigue el último plan. Las tareas propias siguen creándose |
| Tareas de incidente | Son locales y prevalecen. Tierra no las borra |

**Criterios de aceptación**

- Con el enlace cortado, el plan queda en cola y al volver llega, se aplica y se confirma.
- Entregar dos veces el mismo plan deja las tareas una sola vez.
- Lo que la tripulación completó o creó no se pierde al aplicar un plan.

**Hito:** I7 (hora 32, junto con la interfaz de B).

---

### 3.12 F15 · Enlace hacia Tierra y consentimiento · 3 h · P2

**Objetivo:** que Tierra reciba, al reconectar, solo lo que la tripulación autorizó y en orden.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Consume | `monitoring.alert_*`, `facility.incident_*`, `engagement.task_completed · task_created · task_blocked · ground_plan_applied`, `knowledge.recommendation_ready`, `crew.consent_changed`. Lee `ConsentQuery` |
| Publica | `groundlink.link_state_changed`, `groundlink.batch_acknowledged` |
| API | `PUT /api/v1/groundlink/link` (R5), `groundLinkStatus`, `syncGroundLinkNow` |

**Tareas**

- [ ] **15.1 Esquema (0,5 h):** `link_state`, `outbound_batch`, `outbound_item` (estados `queued`, `sent`, `acked`, `withheld`).
- [ ] **15.2 Cola y filtro por consentimiento (1 h):** cada evento relevante se encola. Si su categoría no está compartida queda `withheld`. Sin enlace solo se encola y nada falla.
- [ ] **15.3 Lotes y sincronización (1 h):** al volver el enlace se arma un lote en orden de ocurrencia, sin lo `withheld`. Idempotente por lote. Confirmación de Tierra con demora.
- [ ] **15.4 API y estado del enlace (0,5 h):** R5 simula el corte y la vuelta. `groundLinkStatus` informa cola, última sincronización y estado. Publica `link_state_changed`.

**Criterios de aceptación**

- Nada se sube sin consentimiento de su categoría.
- La cola sobrevive a un reinicio del equipo.
- Reenviar un lote ya confirmado no duplica nada.

---

## 4. Diseño de los módulos de A

### 4.1 Eventos

**Los que A publica (19):**

| Evento | Receptores |
| --- | --- |
| `telemetry.readings_recorded` | Monitoreo, Gateway |
| `telemetry.scenario_changed` | Gateway |
| `monitoring.alert_raised` | Conocimiento (B), Misiones, Gateway, Enlace, Nave |
| `monitoring.alert_acknowledged` | Misiones, Gateway, Enlace |
| `monitoring.alert_resolved` | Misiones, Gateway, Enlace, Nave |
| `engagement.task_assigned` | Gateway |
| `engagement.task_completed` | Gateway, Enlace |
| `engagement.task_created` | Gateway, Enlace |
| `engagement.task_blocked` | Gateway, Enlace |
| `engagement.ground_plan_applied` | Enlace, Gateway |
| `crew.baseline_updated` | Monitoreo |
| `crew.consent_changed` | Enlace |
| `groundlink.link_state_changed` | Gateway |
| `groundlink.batch_acknowledged` | Gateway |
| `groundlink.ground_plan_received` | Misiones, Gateway |
| `facility.incident_opened` | Misiones, Gateway, Enlace |
| `facility.incident_updated` | Gateway, Enlace |
| `facility.incident_resolved` | Misiones, Gateway, Enlace |
| `facility.zone_status_changed` | Gateway |

**Los que A recibe de B (3):** `knowledge.recommendation_ready` (Misiones, Gateway y Enlace), `knowledge.recommendation_enriched` (Gateway) y `assistant.answer_ready` (Gateway).

### 4.2 Lecturas síncronas entre módulos de A

| Quien lee | De quién | Fachada |
| --- | --- | --- |
| Monitoreo | Telemetría | `ReadingQuery` |
| Monitoreo | Tripulación | `BaselineQuery` |
| Nave | Monitoreo | `ActiveAlertsQuery` |
| Misiones | Nave | `ZoneQuery` |
| Enlace | Tripulación | `ConsentQuery` |
| Enlace | Misiones | `TaskStatusQuery` |

**Con B:** Misiones lee `ActionCatalogQuery` (B). B lee `RuleQuery` y `ActiveAlertsQuery` (A).

### 4.3 Mapa de eventos a mensajes WebSocket

| Evento de dominio | Mensaje WebSocket |
| --- | --- |
| `telemetry.readings_recorded` | `telemetry.tick` (coalescido a 1 Hz) |
| `telemetry.scenario_changed` | `scenario.changed` |
| `monitoring.alert_raised · acknowledged · resolved` | `alert.raised · alert.updated · alert.resolved` |
| `knowledge.recommendation_ready · enriched` | `recommendation.ready · recommendation.enriched` |
| `engagement.task_assigned` | `task.assigned` (y `reminder.due` desde el planificador) |
| `facility.incident_opened · updated · resolved` | `incident.opened · incident.updated · incident.resolved` |
| `facility.zone_status_changed` | `zone.status` |
| `groundlink.link_state_changed` | `groundlink.state` |
| `groundlink.ground_plan_received`, `engagement.ground_plan_applied` | `plan.received · plan.applied` |
| `assistant.answer_ready` (y la transcripción) | `assistant.transcript · assistant.token · assistant.answer` |
| (propios del canal) | `subscribe · unsubscribe · resume · ping · pong` |

### 4.4 Flujo de una alerta por zona

1. La lectura entra por R1 y `telemetry` guarda lecturas y `readings_recorded` en una transacción.
2. El relay entrega el evento a Monitoreo, que evalúa el catálogo por zona.
3. Si una regla se dispara, Monitoreo guarda la alerta y `alert_raised` en una transacción.
4. En paralelo reciben el evento: Gateway (lo empuja por WebSocket), Conocimiento de B (arma la recomendación), Nave (abre el ticket), Misiones (crea tareas) y Enlace (lo encola).
5. Nave publica `incident_opened` y `zone_status_changed`. Gateway los empuja.
6. La tripulación reconoce por GraphQL y se publica `alert_acknowledged`.

### 4.5 Esquemas de datos

Las tablas completas de cada esquema están en la sección 7 del plan. Reglas comunes: un esquema por módulo, sin claves foráneas entre esquemas, `evidence_state` y `origin` obligatorios donde corresponda y una migración Alembic por módulo con su propia tabla de versión.

---

## 5. Contratos que A entrega a B

### 5.1 REST (7)

| ID | Ruta | Uso |
| --- | --- | --- |
| R1 | `POST /api/v1/telemetry/readings` | Lotes de lecturas |
| R4 | `POST /api/v1/sim/scenarios/{key}:start · :stop` | Escenarios de la demo |
| R5 | `PUT /api/v1/groundlink/link` | Cortar o restablecer el enlace |
| R6 | `GET /api/v1/rules/catalog.json` | Catálogo de reglas |
| R7 | `GET /health · GET /ready` | Salud (**hecho**) |
| R8 | `POST /api/v1/admin/outbox/{id}:replay` | Reencolar un evento muerto |
| R9 | `POST /api/v1/groundlink/inbound/plans` | Plan desde Tierra |

### 5.2 GraphQL (31 operaciones de A)

| Módulo | Operaciones |
| --- | --- |
| Monitoreo | `dashboard`, `alerts`, `alert`, `rules`, `acknowledgeAlert` |
| Telemetría | `readings`, `zoneReadings` |
| Nave | `ship`, `incidents`, `incident`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| Tripulación | `crewMember`, `setConsent`, `recordBaseline` |
| Misiones | `tasks`, `groundPlan`, `completeTask`, `snoozeReminder`, `createTask`, `updateTask · deleteTask`, `blockTask` |
| Enlace | `groundLinkStatus`, `syncGroundLinkNow`, `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |
| Plataforma | `outboxStats` |

### 5.3 WebSocket (14 mensajes)

`telemetry.tick`, `alert.*`, `recommendation.*`, `task.assigned · reminder.due`, `assistant.transcript`, `assistant.token · answer`, `groundlink.state`, `incident.*`, `zone.status`, `plan.received · applied`, `scenario.changed`, `subscribe · unsubscribe`, `resume`, `ping · pong`.

Mensaje del servidor: `{ "seq": 18342, "topic": "alerts", "type": "alert.raised", "at": "…", "data": { … } }`.

---

## 6. Calidad y pruebas

### 6.1 Matriz

| Nivel | Qué cubre | Herramienta |
| --- | --- | --- |
| Dominio | Funciones puras de PIO₂, ventanas, motor de reglas, anomalías, ciclo de vida | pytest, Hypothesis |
| Contrato | Cada evento contra su modelo. Esquema GraphQL y mensajes WebSocket estables | pytest, generación y comparación del esquema |
| Arquitectura | Reglas de import entre módulos y capas | import-linter y sus canarios |
| Integración | Outbox, relay, migraciones, handlers, GraphQL y WebSocket contra PostgreSQL real | testcontainers |
| Extremo a extremo | Escenario → alerta → ticket → WebSocket → reconocer → normalizar → resolver | pytest con cliente WebSocket |
| Plan desde Tierra | Corte de enlace, llegada tardía, versión repetida, plan corrupto, ítem inválido | pytest, testcontainers |
| Sin conexión | Contenedor sin red: flujo completo con el perfil `jurado` | Manual, en otra computadora |

### 6.2 Vectores de prueba del motor de reglas (obligatorios)

| Entrada | Resultado esperado |
| --- | --- |
| 760 mmHg, 21 % de O₂ | PIO₂ ≈ 149,7 mmHg, normoxia, verde |
| 760 mmHg, 18 % de O₂ | PIO₂ ≈ 128,3 mmHg, amarillo (bajo 145, sobre 127) |
| 56,5 kPa (423,8 mmHg), 34 % de O₂ | PIO₂ ≈ 128,1 mmHg, amarillo, cerca de 127 |
| ppCO₂ promedio de 1 h = 3,1 mmHg | Rojo |
| 14,7 a 12,0 psia en 1 min (Δ 2,7 psi) | 2,7 psi/min, dentro de 13,5. Sin alerta por velocidad |
| Bajada de 14 psi en 0,5 min | 28 psi/min. Alerta de despresurización rápida |

### 6.3 Reglas de las pruebas

- Prueba primero y verla fallar por la razón correcta.
- Las pruebas de integración usan PostgreSQL real, no simulaciones.
- Cada prueba es independiente y prepara sus propios datos.
- Una prueba escrita después del código se marca como tal en el informe de evidencia.

---

## 7. Definición de hecho

Una fase de A está **hecha** cuando:

- [ ] Cumple sus criterios de aceptación.
- [ ] `scripts/check.sh` termina en verde (ruff, mypy estricto, import-linter, pytest con cobertura de 80 % o más).
- [ ] Hay migración reversible si hay tablas nuevas.
- [ ] Los handlers son idempotentes y tienen prueba de duplicado.
- [ ] Todo valor de regla lleva `evidence_state`, y lo que no tiene fuente dice `DEMO`.
- [ ] Funciona sin internet y sin enlace con Tierra.
- [ ] Si toca un contrato, B lo revisó antes.
- [ ] Hay un informe de evidencia en `docs/tdd/` del bloque.
- [ ] La entrada correspondiente está en `docs/bitacora.md`.

---

## 8. Riesgos específicos de A

| Riesgo | Probabilidad | Mitigación |
| --- | --- | --- |
| Las horas de `crew` (línea base y consentimientos) no están asignadas a una fase | Alta | Se absorben en F2 (fachada de línea base) y F15 (consentimiento). Si no alcanzan, es el primer desvío: avisar a B y al usuario |
| Un cambio de contrato rompe la interfaz de B sin avisar | Media | Esquemas exportados desde F5 y tipos generados en la CI de B. Revisión de B antes de cambiar |
| La alerta por tendencia genera ruido y tickets falsos | Media | Mínimo de cambio por métrica, mínimo de 65 puntos de historia, y la tendencia solo avisa (no abre ticket) |
| Sondeo y `NOTIFY` no alcanzan la meta de 1 s | Media | `LISTEN/NOTIFY` ya implementado. Medir antes del demo y registrar el resultado |
| El relay se vuelve un cuello de botella o pierde orden | Media | Un solo worker con orden por id. Partición por `partition_key` solo si hace falta. Pruebas de orden y duplicados |
| Plan de Tierra corrupto, repetido o fuera de orden | Media | Hash de integridad, versión creciente, aplicación atómica y rechazo con motivo |
| Conflictos entre el plan de Tierra y las tareas locales sin enlace | Alta | Reglas de conflicto probadas una por una (sección 3.11) |
| `reading` crece sin control | Baja | Particionado por día e índice BRIN. Retención configurable |
| Con las ventanas reales de 1 h, Monitoreo consulta unas 3.600 muestras por métrica y zona en cada lote | Media | Hoy se evalúa con lecturas crudas. Si pesa, usar `rollup_mean` (ya existe) para las ventanas largas. Medir antes del demo |
| El hito I2 depende del gateway, que llega en F5 | Media | B sigue con sus grabaciones hasta I5. Registrado como inconsistencia del plan |
| Falta de `make` y del puerto 5432 libre en equipos ajenos | Baja | `scripts/check.sh` y `SPACEAPP_DB_PORT` |
| Si A falta, B no conoce el núcleo | Media | README corto por módulo, informes TDD y pruebas de contrato como documentación |

---

## 9. Coordinación con Dev B

**Qué le entrega A a B**

1. **I0 (hora 1):** contratos, registro de eventos y bus en memoria. **Listo para revisión.**
2. **I1 (hora 4):** outbox real. **Disponible.**
3. **I2 a I5:** lecturas por zona, incidencias y gateway reales, para que B retire sus mocks.
4. **F5:** `schema.graphql`, OpenAPI y `ws-messages.schema.json` para generar tipos y mocks.
5. `alert_raised` con `zone_id` y las fachadas `RuleQuery` y `ActiveAlertsQuery`.

**Qué necesita A de B**

1. `recommendation_ready` y la fachada `ActionCatalogQuery` (Misiones las usa).
2. `assistant.answer_ready` para que el gateway lo convierta en mensajes WebSocket.
3. Los resolvers de Conocimiento y Asistente, para componer el esquema.

**Cuándo avisar**

- Si un contrato necesita un campo nuevo: **antes** de implementarlo, con una solicitud al dueño.
- Al terminar cada fase: una línea con qué quedó listo y qué falta.
- Al detectar que un mock de B no refleja el comportamiento real.

**Pendiente para la primera reunión con B:** revisar el bus en memoria, la firma de los handlers (`HandlerContext`) y el registro de eventos.

---

## 10. Decisiones pendientes que afectan a A

No se deciden sin consultar. Mientras tanto se usa el supuesto indicado.

| # | Decisión | Supuesto actual |
| --- | --- | --- |
| 1 | ~~Falta un evento de escalada de severidad.~~ **Resuelto en F2:** cada regla tiene severidad fija y subir de nivel es resolver la alerta leve y levantar la grave, así que no hace falta `monitoring.alert_escalated`. Queda por acordar con B si el gateway mapea `alert.updated` al reconocimiento | Sin evento nuevo |
| 2 | Nombre de la variable de perfil y valor por defecto | `SPACEAPP_PROFILE` con `jurado` |
| 3 | Autenticidad del plan de Tierra | Solo hash de integridad. La firma criptográfica queda como mejora |
| 4 | Alcance del panel de Tierra | La misma SPA con rol `ground` y enlace simulado |
| 5 | Qué comparte Tierra por defecto | Categoría «tareas» activa por defecto |
| 6 | Reglas de radiación (nivel 2 del documento de contexto) | Fuera de F2. Los tipos `AUTO` de radiación quedan como reglas pendientes |
| 7 | Umbrales de frecuencia cardíaca, presión arterial y SpO₂ | `DEMO` hasta tener una fuente citable (por ejemplo NEWS2, sin verificar) |
| 8 | Usuarios reales para `CODEOWNERS` | Marcadores `@dev-a` y `@dev-b` |
| 9 | Escenario de la demo (tránsito a Marte, base lunar o ISS) | Nave de tránsito. Cambiar es cambiar datos |

---

## 11. Checklist maestro de Dev A

**Corte P0 (21,5 h): 11 h hechas**

- [x] F0 · Cimientos: contratos, bus en memoria, perfiles y arquitectura (I0, en revisión de B)
- [x] F1 · Outbox, relay, inbox y `/ready` (I1)
- [x] F2 · Catálogo de reglas, motor con los seis vectores, anomalías y alertas
- [x] F3 · Ingesta por lotes, simulador con escenarios por zona y rollup (I2, parte del simulador)
- [ ] F4 · Plano, catálogo de 61 tipos, tickets automáticos y manuales, estado de zonas (I3)
- [ ] F5 · Esquema GraphQL compuesto, gateway `/ws`, contratos exportados (I5)
- [ ] F9 · Dockerfile, compose y prueba sin internet (I6)

**P1 y P2 (9,5 h)**

- [ ] F10 · Plantillas, tareas con origen y tareas propias
- [ ] F11 · Plan desde Tierra, aplicación con reglas de conflicto (I7)
- [ ] F15 · Cola hacia Tierra con consentimiento y sincronización

**Cierre**

- [ ] README corto por módulo
- [ ] Informe de evidencia de cada bloque en `docs/tdd/`
- [ ] Entrada de cada bloque en `docs/bitacora.md`
- [ ] Prueba final en otra computadora, sin internet, con el perfil `jurado`
