# Dev A tasks · core and realtime

> NASA Space Apps 2026 · health monitor for astronauts
> Working document for **Dev A**. Derived from [`architecture-plan.md`](architecture-plan.md) (sections 5 to 8, 10, 13 and 16) and from [`spaceapps-health-monitor-context.md`](spaceapps-health-monitor-context.md). It is the counterpart of [`tasks-dev-b.md`](tasks-dev-b.md).
> History and status: [`logbook-dev-a.md`](../logbook-dev-a.md). Evidence of the tests already done: [`tdd/f0-f1.tdd.md`](tdd/f0-f1.tdd.md).
> Hours are working hours per person, not wall-clock.

---

## 0. Summary

| | |
| --- | --- |
| **Role** | Owner of the platform (outbox and relay), telemetry, monitoring and rules, facility, crew, missions and tasks, ground link and the GraphQL and WebSocket gateway |
| **Hours** | 31 h in total. 21.5 h in the P0 cut and 9.5 h in P1 and P2 |
| **Done** | **F0, F1, F2 and F3** (11 h). 293 tests, 97.53 % coverage (see section 3.4) |
| **To do** | F4, F5, F9, F10, F11 and F15 (20 h) |
| **Language** | Python 3.12 with FastAPI, async SQLAlchemy 2, PostgreSQL 16 with pgvector, Strawberry (GraphQL, still to be added) |
| **Partner** | Dev B: the whole SPA and the `knowledge` and `assistant` modules (all of the RAG) |
| **Golden rule** | Contracts are frozen first. B works on mocks until A makes them real |

### Dev A timeline

| Hours | Phase | Name | Priority | Effort | Status |
| --- | --- | --- | --- | --- | --- |
| 0 to 1 | F0 | Foundations (joint with B) | P0 | 1 h | **Done** |
| 1 to 4 | F1 | Event bus with outbox | P0 | 3 h | **Done** |
| 4 to 8 | F2 | Monitoring and rule catalog | P0 | 4 h | **Done** |
| 8 to 11 | F3 | Telemetry and per-zone simulator | P0 | 3 h | **Done** |
| 11 to 16 | F4 | Ship, zones and incidents (backend) | P0 | 5 h | Pending |
| 16 to 20 | F5 | GraphQL and WebSocket | P0 | 4 h | Pending |
| 20 to 21 | | Slack (A waits for B for the delivery) | | 1 h | |
| 21 to 22.5 | F9 | Jury delivery (joint) | P0 | 1.5 h | Pending |
| 22.5 to 25 | F10 | Tasks: backend | P1 | 2.5 h | Pending |
| 25 to 29 | F11 | Plan from Ground: backend | P1 | 4 h | Pending |
| 29 to 32 | F15 | Ground link and consent | P2 | 3 h | Pending |

**The 1 h of slack** is for integration tests with B and for reviewing contracts. It is not assigned to more work.

### Milestones in which A takes part

| Milestone | Hour | What A delivers | Status |
| --- | --- | --- | --- |
| I0 · Contracts frozen | 1 | Each module's `contracts.py`, `event_registry.py`, in-memory bus | **Ready for B's review** |
| I1 · Real outbox | 4 | Outbox, relay and inbox | **Available** |
| I2 · Live readings and simulator | 11 | The simulator emits per-zone readings. B connects the WebSocket ticks | **Simulator ready.** The WebSocket ticks depend on the gateway (F5), so B uses its recordings until I5 |
| I3 · Live incidents | 16 | Tickets, zones and type catalog. B connects the ship panel | Pending |
| I5 · Complete GraphQL and WebSocket | 20 | B removes all the mocks. First end-to-end test | Pending |
| I6 · Jury delivery | 22.5 | Docker image tested without internet | Pending |
| I7 · P1 complete | 32 | Plan from Ground end to end | Pending |

(I4, alert with cited recommendation, depends on B's F8.)

**Inconsistency detected in the plan:** milestone I2 asks to connect the ticks over WebSocket, but the gateway is phase F5 (hour 20). Until then B keeps using its message recordings and I2 is met only on the simulator side.

---

## 1. Scope

### 1.1 What belongs to A

| Module | What it does | Tables |
| --- | --- | --- |
| `platform` | Outbox, relay, inbox, `UnitOfWork`, profiles, configuration, `/health` and `/ready` | `outbox_event`, `inbox_processed` |
| `telemetry` | Readings of the body, zones and radiation; per-minute rollup; simulator with scenarios | `sensor`, `reading`, `reading_rollup_1m`, `scenario_run` |
| `monitoring` | Rule catalog, PIO₂, windows, trend anomalies, alert lifecycle | `rule`, `alert`, `alert_ack` |
| `facility` | Habitat and zone floor plan, incident tickets, catalog of 61 types, color status of each zone | `habitat`, `zone`, `incident_type`, `incident`, `incident_update` |
| `crew` | Profiles, baseline and consents | `crew_member`, `baseline`, `consent` |
| `engagement` | Templates and tasks with origin, own tasks, reminders, streaks and achievements | `task_template`, `task`, `reminder`, `achievement`, `crew_achievement` |
| `groundlink` | Link in both directions: queue toward Ground and plan from Ground | `link_state`, `outbound_batch`, `outbound_item`, `inbound_plan`, `ground_plan`, `ground_template` |
| `realtime` | WebSocket gateway. It has no tables | |

### 1.2 What does not belong to A

- The `knowledge` and `assistant` modules and all of the RAG (Ollama, Whisper, Alexa): they belong to B.
- The whole SPA (`web/`): it belongs to B.
- The GraphQL resolvers for Knowledge and Assistant: B writes them. **A composes the schema and registers them.**

### 1.3 Project rules A must respect

1. **The rules engine is deterministic and auditable.** The language model never decides an alert.
2. **Oxygen is evaluated as partial pressure**, not as a percentage: `PIO₂ = (P_total − 47 mmHg) × FO₂`. The same holds for CO₂.
3. **Every figure without a verified source is labeled `DEMO`.** The yellow bands are a team proposal and also.
4. **Body and simulator data carry `origin = SIMULATED`** all the way to the interface.
5. **A single owner per module.** A module only imports another's `contracts` and `facade`. `import-linter` enforces it.
6. **One PostgreSQL schema per module and no foreign keys between schemas.**
7. **A state change and its event are written in the same transaction** (`UnitOfWork`). Nobody publishes from outside it.
8. **Handlers are idempotent** by `(consumer, event_id)`.
9. **The alert never waits for a language model.**
10. **The system works without internet and without a ground link.**
11. **No commits are made** unless the user asks for them.

---

## 2. How A works

### 2.1 TDD in every phase

For every phase: write the test, **watch it fail for the right reason** (RED), write the minimal code, watch it pass (GREEN), refactor and check coverage (minimum 80 %). Each block closes with an evidence report in `docs/tdd/`.

### 2.2 What already exists in the repository

| Path | Content |
| --- | --- |
| `src/spaceapp/platform/events.py` | `EventEnvelope`, `EventPayload` |
| `src/spaceapp/platform/bus.py` | `EventBus`, `EventPublisher`, `HandlerContext`, `SubscriptionRegistry`, `InMemoryEventBus` |
| `src/spaceapp/platform/outbox/` | `UnitOfWork`, `add_to_outbox`, `OutboxRelay`, `backoff_seconds`, `outbox_stats` |
| `src/spaceapp/platform/{profiles,config,db,vocab,migrate}.py` | Profiles, configuration, database, shared vocabulary, migrations |
| `src/spaceapp/modules/*/contracts.py` | The 22 events |
| `src/spaceapp/event_registry.py` | Event registry |
| `src/spaceapp/main.py` | `create_app` with `/health` and `/ready` |
| `migrations/platform/` | Outbox and inbox migration |
| `tests/` | 293 tests (unit, contract, architecture, integration and end to end) |
| `docker/compose.yaml` | PostgreSQL with pgvector on port 5433 |
| `scripts/check.sh` | ruff, mypy, import-linter and pytest with coverage |
| `tools/docgen/` | Generator of the plan and the artifact |
| `src/spaceapp/modules/monitoring/` | Domain (units, PIO₂, series, trend, rules, engine, lifecycle), JSON catalog, SQL and in-memory repository, readings handler, acknowledge alert, `RuleQuery` and `ActiveAlertsQuery` facades, `GET /api/v1/rules/catalog.json` |
| `src/spaceapp/modules/telemetry/` | Readings and sensors, simulator with scenarios, idempotent ingestion, per-minute rollup, `SqlReadingQuery` facade, R1 and R4 |
| `src/spaceapp/platform/ids.py` | Stable identifiers for habitat, zone and sensor |
| `rules/catalog/monitoring.json` | Catalog of 25 rules with source and evidence state |
| `data/telemetry/sim_layout.json` | The 10 simulated zones |
| `migrations/{monitoring,telemetry}/` | Each schema's own migrations |

### 2.3 How a handler is written

A handler receives `(event, HandlerContext)`. It is written **once** and runs the same on the in-memory bus (`ctx.session` is `None`) and on the real outbox (`ctx.session` is the handler's transaction). To publish a derived event, use `ctx.publish(...)`: with the real outbox it lands in the same transaction and is discarded if the handler fails.

```python
async def on_readings_recorded(event: EventEnvelope, ctx: HandlerContext) -> None:
    payload = event.payload_as(ReadingsRecorded)
    ...  # use case logic
    await ctx.publish(EventEnvelope.from_payload(AlertRaised(...), ...))
```

### 2.4 Structure of a module

```text
src/spaceapp/modules/<module>/
  domain/            # rules and aggregates. No FastAPI, SQLAlchemy or Strawberry
  application/       # use cases and handlers
  ports/             # inbound and outbound interfaces
  adapters/
    inbound/         # rest.py, graphql.py, events.py
    outbound/        # sql.py and the adapters of each port
  contracts.py       # public events. The only thing other modules import
  facade.py          # read-only queries exposed to other modules
migrations/<module>/ # own Alembic and own version table
```

Allowed layers: `adapters` > `application` > `ports` > `domain`.

### 2.5 Commands

```bash
scripts/check.sh                                              # ruff, mypy, import-linter, pytest + coverage
docker compose -f docker/compose.yaml up -d --wait postgres   # local database (port 5433)
uv run python -m spaceapp.platform.migrate <module>           # applies migrations
uv run uvicorn --factory spaceapp.main:create_app             # API
```

The integration tests need Docker running (`systemctl --user start docker-desktop`).

### 2.6 Conventions

- **Branches:** `a/<phase>-<topic>`, under 2 h.
- **Contracts:** a change in `contracts.py`, in the GraphQL schema or in the WebSocket messages requires B's review **before** implementing it.
- **`CODEOWNERS`:** `@dev-a` and `@dev-b` must be replaced with the real users.

---

## 3. Phases in detail

### 3.1 F0 · Foundations (joint with B) · 1 h · P0 · **DONE**

**Goal:** leave repository, contracts and tools ready to work in parallel.

- [x] **0.1 Project and tools (0.25 h):** `uv`, Python 3.12, `pyproject.toml`, ruff, strict mypy, pytest, import-linter.
- [x] **0.2 Structure and contracts (0.25 h):** 9 modules with their hexagonal skeleton and the 22 events as Pydantic models with `extra="forbid"`.
- [x] **0.3 Event envelope and in-memory bus (0.25 h):** `EventEnvelope` with a validated `module.fact` type and `InMemoryEventBus` (idempotent, FIFO, isolated errors).
- [x] **0.4 Profiles, composition root and architecture rules (0.25 h):** `dev1`, `dev2`, `jury`; `create_app`; 4 import-linter contracts with 4 canaries; `docker/compose.yaml`.

**Meets:** I0. **Only B's review is pending** (section 8).

### 3.2 F1 · Event bus with outbox · 3 h · P0 · **DONE**

**Goal:** store state and event in one transaction and deliver each event at least once, without repeating work.

- [x] **1.1 Migration (0.5 h):** `platform.outbox_event` (with `version`, `correlation_id` and `causation_id`), `platform.inbox_processed`, partial index of pending rows and status constraint.
- [x] **1.2 `UnitOfWork` and publisher (0.5 h):** state and event in the same transaction. `NOTIFY` only on commit.
- [x] **1.3 Relay (1.25 h):** `LISTEN/NOTIFY` with fallback polling, `FOR UPDATE SKIP LOCKED`, order by id, backoff 1 to 60 s, move to `dead` after 8 attempts, one handler per transaction with its mark in the inbox, isolation between consumers.
- [x] **1.4 `/health` and `/ready` (0.25 h):** pending, dead and lag of the oldest event. 503 if the database does not respond.
- [x] **1.5 Integration tests (0.5 h):** atomicity, duplicates, relay crash, backoff, `dead`, order, concurrency.

**Meets:** I1.

### 3.3 Differences with respect to the original plan (already applied)

| Plan | What was built | Reason |
| --- | --- | --- |
| Handler `async def h(event)` | `h(event, HandlerContext)` | A single handler runs in memory and on the outbox, and can publish in the same transaction |
| Outbox table without `version` or correlation | `version`, `correlation_id`, `causation_id` were added | They are in the event envelope |
| Database port 5432 | 5433 (`SPACEAPP_DB_PORT`) | 5432 is used by another project of the user |
| `make check` | `scripts/check.sh` | `make` is not installed |
| Trend detector with 65 history points | Windows and minimums **per rule** (`params`) | With the atmosphere sampled every 5 s (V2 6001) there would never be 65 points. CO₂ and PIO₂ use a baseline of 120 to 30 s. Temperature and humidity, sampled every minute, use 20 to 5 min |
| `env-dpdt` with a 60 s window | 10 s window | A real leak averages about 6 psi/min over 60 s and did not reach 13.5. Over 10 s it reaches ~16 |
| Severity escalation as an event | Rule replacement | Each rule has a fixed severity: going up a level means resolving the mild alert and raising the serious one. `monitoring.alert_escalated` is not needed |
| 1 h-window rules always active | They require the data to cover at least half of the window | Prevents a spike at startup from counting as a 1 h average. Demo time is accelerated with `rule_window_scale`, without making up data |
| `crew.baseline_updated` handler (2.5) and `BaselineQuery` (2.6) | **Not done** | There are no baseline-relative rules (level 3) yet that would use them. They are done together with those |
| Simulator clock | Exact exponential approximation | The result does not depend on the size of the time step |

### 3.4 Evidence

293 tests pass (122 from Block 1, 3 from the document generator and 168 from Block 2), coverage 97.53 %, ruff and strict mypy without errors, 4 architecture contracts met. Detail in [`tdd/f0-f1.tdd.md`](tdd/f0-f1.tdd.md) and [`tdd/f2-f3.tdd.md`](tdd/f2-f3.tdd.md).

---

### 3.5 F2 · Monitoring and rule catalog · 4 h · P0 · **DONE**

**Goal:** that every reading is evaluated deterministically against a catalog of rules with a source, and that the alert lifecycle is consistent.

**Depends on:** F1. **Enables:** F3 (consumes readings), F4 (consumes alerts) and B's milestone I4.

**Contracts**

| Direction | Contract |
| --- | --- |
| Consumes | `telemetry.readings_recorded` (latest values per sensor and zone), `crew.baseline_updated`. Reads `ReadingQuery` from Telemetry and `BaselineQuery` from Crew |
| Publishes | `monitoring.alert_raised`, `monitoring.alert_acknowledged`, `monitoring.alert_resolved` |
| Exposes | `RuleQuery` facades (used by Knowledge, B's) and `ActiveAlertsQuery` (used by Facility and Assistant). `GET /api/v1/rules/catalog.json` |

**Rule values (from the context document, section 5.2)**

| Rule | Value | Requirement | State |
| --- | --- | --- | --- |
| `env-co2-1h` | 1 h average ppCO₂ ≤ 3 mmHg. Pre-alert from 2.5. Above 4.5, fatigue and nausea | V2 6004. TB-004 | `VERIFIED`. The pre-alert is `DEMO`. The 4.5 value is `TB` |
| `env-pio2` | Normoxia 145 to 155 mmHg. Red below 127. Critical at 122 or less (1 h average). Red above 356. Yellow below 145 and above 155 | V2 6003, Table 6.2-1 | Limits `VERIFIED`. Yellows `DEMO` |
| `env-ptotal` | 34.5 < P ≤ 103 kPa | V2 6006 | `VERIFIED` |
| `env-dpdt` | Pressure change ≤ 13.5 psi/min if it exceeds 1.0 psi | V2 6007 | `VERIFIED` |
| `env-n2` | Diluent gas ≥ 30 % | V2 6002 | `VERIFIED` |
| `env-rh`, `env-t` | Performance zone 20 to 25 °C and 30 to 60 % RH. Health limit 18 to 27 °C and 25 to 75 % RH | V2 6012 and V2 6013 | `DEMO` approximation (the text only gives the anchors of the figure) |

Conversions: 1 kPa = 7.50062 mmHg. 1 psi = 51.7149 mmHg.

**Tasks**

- [x] **2.1 Rule catalog (0.75 h)**
  - Versioned JSON in `rules/catalog/` with: `key`, `kind` (`threshold` or `trend`), `parameter`, `operator`, `threshold`, `unit`, `window_s`, `severity`, `source_requirement`, `source_document`, `evidence_state`, `hrp_hazard`, `action_key`, `active`.
  - Loader with validation: a rule without a source or without an evidence state does not load. A `DEMO` rule is labeled as such.
  - Migration of `monitoring.rule`, `alert` and `alert_ack` in `migrations/monitoring/`.
- [x] **2.2 Pure domain functions (0.75 h)**
  - Pressure conversions, `PIO₂ = (P − 47) × FO₂`, CO₂ partial pressure, moving windows (1 h average) and pressure rate of change.
  - No I/O. Tests with Hypothesis (properties) in addition to the cases.
- [x] **2.3 Per-zone evaluation engine (1 h)**
  - `evaluate(readings, rules)` returns the hits with value, band, rule and evidence. It evaluates each zone separately.
  - **Six mandatory test vectors** (section 6.2).
- [x] **2.4 Trend anomaly detector (0.5 h)**
  - Compares the mean of the last 5 s with the previous 40 s (window from −60 to −20 s). Flags an anomaly if the change exceeds the maximum between 4σ and a per-metric minimum: CO₂ 0.6 mmHg, humidity 6 %, temperature 1.5 °C, PIO₂ 6 mmHg, pressure 4 kPa.
  - Requires at least 65 history points. Always `DEMO`. It does not fire on normal noise and does fire on a sustained drift.
- [x] **2.5 Alert lifecycle (0.5 h)** (without the `baseline_updated` handler: see differences)
  - States `raised`, `acknowledged`, `resolved`. Deduplication by `(rule, zone)` while it stays active (partial unique index). Hysteresis so it does not flicker.
  - Handler for `readings_recorded` and `baseline_updated`. Publishes through the outbox in the same transaction.
  - Acknowledging is idempotent.
- [x] **2.6 Facades (0.25 h):** `RuleQuery` and `ActiveAlertsQuery` in `facade.py`. Crew's `BaselineQuery` is left for when baseline-relative rules exist.
- [x] **2.7 Export the catalog (0.25 h):** `GET /api/v1/rules/catalog.json` with caching by version.

**Acceptance criteria**

- The six test vectors give the expected result.
- The same reading evaluated twice does not duplicate the alert.
- A rule without a source or without an evidence state does not load.
- Every alert carries rule, measured value, document, requirement and evidence state.
- `import-linter` green.

**How it turned out (summary):** the catalog has 25 rules (20 threshold and 5 trend). The engine evaluates per zone and is pure. A more serious rule replaces the mild ones (`supersedes`). The lifecycle uses a hysteresis of 3 evaluations. The alert is stored with its evidence and the event in the same transaction. Acknowledging is idempotent. The 6 test vectors give the expected result.

**Milestone:** feeds I2 (together with F3) and I4 (with B's F8).

---

### 3.6 F3 · Telemetry and per-zone simulator · 3 h · P0 · **DONE**

**Goal:** receive readings in batches idempotently and produce realistic simulated data per zone.

**Depends on:** F1. **Enables:** I2.

**Contracts**

| Direction | Contract |
| --- | --- |
| Publishes | `telemetry.readings_recorded` (one event per batch, with the latest values per sensor and zone), `telemetry.scenario_changed` |
| Exposes | `POST /api/v1/telemetry/readings` (R1), `POST /api/v1/sim/scenarios/{key}:start · :stop` (R4). `ReadingQuery` facade |

**Sampling frequencies from the standard (V2 6001, Table 6.1-1):** atmosphere every 5 s, pressure every 1 s, temperature and humidity every 1 min.

**Tasks**

- [x] **3.1 `telemetry` schema (0.75 h):** `sensor` (with `zone_id` and `origin`), `reading` **partitioned by day** with a BRIN index on `ts`, `reading_rollup_1m` and `scenario_run`. Own migration.
- [x] **3.2 Batch ingestion (0.75 h):** R1 answers `202`. Idempotent by `(sensor_id, ts)`. Batches of up to 500 readings. A single `readings_recorded` per batch, never one per reading.
- [x] **3.3 Rollup and `ReadingQuery` (0.5 h):** the handler maintains `reading_rollup_1m`. The facade returns window averages (for example 1 h ppCO₂).
- [x] **3.4 Simulator with scenarios (0.75 h):** zones with nominal values (101.3 kPa, 21 % O₂, CO₂ 0.4 to 1.1 mmHg, 21 to 24 °C, 36 to 52 % RH) with noise. Scenarios: normal, slow CO₂, pressure leak, high humidity, O₂ failure, heat. Controlled through R4. Origin `SIMULATED`.
- [x] **3.5 End-to-end test (0.25 h):** CO₂ scenario → `readings_recorded` → `alert_raised` in the outbox.

**Acceptance criteria**

- Sending the same batch twice leaves the readings only once.
- All simulator data carries `origin = SIMULATED`.
- A slow CO₂ scenario first produces the trend anomaly and then the threshold alert.
- With the simulator off, the system starts just the same.

**How it turned out (summary):** 50 simulated sensors (5 per zone, with the standard's sampling period). Ingestion uses `INSERT … ON CONFLICT DO NOTHING` and publishes a single event per batch with the latest values. `reading` is partitioned by day and partitions are created on ingestion. Zone and sensor identifiers are stable (`platform/ids.py`) so Facility matches without importing Telemetry. The relay and the simulator start with the application only if requested (`SPACEAPP_RELAY_ENABLED`, `SPACEAPP_SIMULATOR_AUTOSTART`).

**Live test:** with the real clock, 130 s of normal operation gave 1,930 readings and no alert. When the CO₂ scenario was triggered in the laboratory, the trend (Attention), the pre-alert (Attention) and the verified alert (Alert) appeared, the first two resolved by replacement. Only that zone was altered, the outbox was left empty and there were no errors.

**Milestone:** I2 (hour 11), on the simulator side.

---

### 3.7 F4 · Ship, zones and incidents (backend) · 5 h · P0

**Goal:** that every zone alert opens a ticket with type, description, severity and location, and that every zone has its color status.

**Depends on:** F2 and F3. **Enables:** I3 and B's ship panel (F7).

**Contracts**

| Direction | Contract |
| --- | --- |
| Consumes | `monitoring.alert_raised`, `monitoring.alert_resolved`. Reads `ActiveAlertsQuery` from Monitoring |
| Publishes | `facility.incident_opened`, `incident_updated`, `incident_resolved`, `zone_status_changed` |
| GraphQL | `ship`, `incidents`, `incident`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |

**Tasks**

- [x] **4.1 `facility` schema (0.75 h):** *(B-019. Difference: there is no `incident_type` table, the catalog lives in memory like the floor plan; there is a `zone_alert`, a projection of the active alerts per zone)* `habitat`, `zone` (with `layout` JSON and `status`), `incident_type`, `incident`, `incident_update`. Own migration. One automatic ticket per active zone (`source_alert_id` as a soft reference).
- [x] **4.2 Floor plan in JSON (0.5 h):** *(B-019: `data/facility/plan.json`, with the artifact's geometry)* the floor plan of the 10 zones (engineering, life support, laboratory, infirmary, bridge, airlock, storage, gym, galley and crew quarters) as data in `data/facility/`. **Switching from a ship to a lunar base means changing data, not code.** All `DEMO`.
- [x] **4.3 Incident type catalog (0.75 h):** *(B-019: `data/facility/incident_types.json`, with exact rule keys and 20 pending rules)* 61 types in 12 categories as versioned data (the catalog is in `tools/docgen/data.py`). Loader with validation. Test: every rule key of an `AUTO` type exists in the rule catalog, or is in an explicit list of pending rules.
- [x] **4.4 Alert handlers (1.5 h)** *(B-019)*
  - `alert_raised` with severity Alert or higher opens an automatic ticket per zone. The trend (severity Attention) does **not** open a ticket.
  - One open ticket per zone: if more alerts arrive its description is updated and, if the severity rises, `incident_updated` is published.
  - `alert_resolved` marks "values normal, can be closed". **The ticket does not close by itself.**
  - An automatic ticket cannot be resolved while there are active alerts in its zone. A manual one can.
  - Manual report (`reportIncident`) by category and type, with default severity and actions.
- [x] **4.5 Color status of each zone (0.5 h):** *(B-019: it is rebuilt the first time the process needs it)* maximum between the active alerts and the open tickets. It is recomputed on startup with `ActiveAlertsQuery`. Publishes `zone_status_changed` only if it changes.
- [~] **4.6 GraphQL (1 h):** *(B-019: everything except the DataLoaders; each ticket's `updates` makes one query)* queries and mutations with typed results (a `union` of success and errors, no exceptions for expected errors), cursor pagination and DataLoaders.

**Acceptance criteria**

- An `alert_raised` of severity Alert in a zone opens exactly one ticket and the zone turns red in the same transaction.
- A second alert in the same zone does not open another ticket.
- An automatic ticket with out-of-range values cannot be resolved.
- Changing the floor plan JSON changes the zones returned by `ship`.
- Restarting the service rebuilds the state of the zones.

**Milestone:** I3 (hour 16).

---

### 3.8 F5 · GraphQL and WebSocket · 4 h · P0

**Goal:** that B consumes a complete and stable GraphQL schema and WebSocket channel.

**Depends on:** F4. **Enables:** I5. **Add dependency:** `strawberry-graphql[fastapi]`.

**Tasks**

- [~] **5.1 Schema composition (1.5 h)** · *partial (B-017): the Monitoring, Telemetry and Knowledge queries, and `acknowledgeAlert`. Missing `crewMember`, `recordBaseline`, `setConsent`, the ship ones (F4), the per-module fragments and the DataLoaders*
  - Strawberry mounted on FastAPI. Each module contributes its fragment (`graphql.py`) and A composes them in `interfaces/graphql/schema.py`. B's resolvers (Knowledge and Assistant) are registered without A writing them.
  - A's queries and mutations: `dashboard`, `readings`, `alerts`, `alert`, `rules`, `zoneReadings`, `crewMember`, `acknowledgeAlert`, `recordBaseline`, `setConsent`, and the ship ones from F4.
  - Typed results with `union`. Depth and cost limit. DataLoaders against N+1.
- [~] **5.2 `/ws` gateway (1.5 h)** · *done (B-017 and B-018). Difference: the topics are `telemetry`, `alerts` and `assistant`, the ones B's interface already uses; `habitat` arrives with F4 and `crew` with Crew*
  - One endpoint with `subscribe` and `unsubscribe` per topic (`habitat`, `crew`, `alerts`, `assistant`).
  - Translates the bus events into the plan's 14 messages (table in section 5.3). `seq` is the outbox `id` when the message comes from an event.
  - **`resume { after_outbox_id }`:** resends from `outbox_event` (24 h retention).
  - `ping` and `pong` every 15 s.
  - **Backpressure:** queue of 500 messages per client. `telemetry.tick` messages are dropped first. **Alerts are not dropped.**
- [x] **5.3 Coalesced ticks (0.25 h):** *(B-017: each client's queue keeps the latest tick per zone and metric)* `telemetry.tick` at 1 Hz at most per zone and sensor, from `readings_recorded`.
- [x] **5.4 Published contracts and operations (0.5 h):** *(B-018: `contracts/schema.generated.graphql`, `openapi.json` and `ws-messages.schema.json` with `python -m spaceapp.interfaces.contracts_export`; B's draft `schema.graphql` is not touched)* export `schema.graphql`, the OpenAPI and `ws-messages.schema.json` so B generates types and mocks. Requeue route `POST /api/v1/admin/outbox/{id}:replay` (R8) and `outboxStats` (development profiles only). Cleanup of `done` events older than 24 h.
- [x] **5.5 End-to-end test (0.25 h):** *(B-017: `tests/integration/test_end_to_end.py`, measured latency 47 to 73 ms)* scenario → alert over WebSocket in under 1 s → acknowledge via GraphQL.

**Acceptance criteria**

- A client that drops and resumes with `resume` receives what was missed, without duplicates.
- With the queue full, ticks are dropped and never alerts.
- `schema.graphql` and `ws-messages.schema.json` regenerate without changes if the contract did not change.
- A CO₂ scenario reaches a WebSocket client in under 1 s (to be measured, it is a proposed goal).

**Milestone:** I5 (hour 20). B removes all the mocks.

---

### 3.9 F9 · Jury delivery (joint with B) · 1.5 h for A · P0

**Goal:** that the jury runs everything with one command and without internet.

**Depends on:** F5, F7 and F8 (hour 21).

- [ ] **9.1 Backend Dockerfile (0.5 h):** image with Python 3.12, pinned dependencies and an unprivileged user.
- [ ] **9.2 Full compose (0.25 h):** application and PostgreSQL with pgvector, with the `jury` profile by default and a visible profile variable.
- [ ] **9.3 Migrations on startup (0.25 h):** each module's migrations are applied in order and idempotently.
- [ ] **9.4 Test on another computer (0.5 h, with B):** without internet, without a GPU and with the microphone blocked.

**Acceptance criteria:** a single command brings up the backend, database and SPA with the `jury` profile. Without Ollama, the template recommendation with a citation keeps working.

**Milestone:** I6 (hour 22.5).

---

### 3.10 F10 · Tasks, backend · 2.5 h · P1

**Goal:** daily health, ship and incident tasks with origin, and the crew's own tasks.

**Depends on:** F9. **B builds the interface** on mocks until A finishes.

**Contracts**

| Direction | Contract |
| --- | --- |
| Consumes | `monitoring.alert_raised · alert_acknowledged · alert_resolved`, `facility.incident_opened · incident_resolved`, `knowledge.recommendation_ready` (B's). Reads `ActionCatalogQuery` (B's) and `ZoneQuery` |
| Publishes | `engagement.task_assigned`, `task_completed`, `task_created`, `task_blocked` |
| GraphQL | `tasks`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask`, `snoozeReminder` |

**Tasks**

- [x] **10.1 Schema (0.5 h):** *(B-022. Difference: no `reminder`, `achievement` or `crew_achievement` tables; snoozing moves `due_at` and the streak is computed from the tasks of the day; `applied_plan` was added)* `task_template`, `task` (with `kind`, `origin`, `template_id`, `blocked_reason`), `reminder`, `achievement`, `crew_achievement`.
- [x] **10.2 Handlers (0.75 h):** *(B-022)* incident tasks are born when a ticket opens and are completed when it closes. An alert's measures are born from the recommendation.
- [x] **10.3 Own tasks (0.75 h):** *(B-022)* `CREW` can create, edit and delete. **A Ground task cannot be edited or deleted:** it returns a typed error. It can be completed, snoozed or **blocked with a reason** (it is not deleted).
- [x] **10.4 GraphQL (0.5 h):** *(B-022: `snoozeTask` instead of `snoozeReminder`; no achievements, only `streak`)* resolvers and typed errors. Only health routines add to the streak and to the achievements. **Critical alerts are not gamified.**

**Acceptance criteria**

- An own task is created without a ground link.
- An incident task is completed when its ticket is resolved.
- A Ground task refuses to be edited or deleted with a typed error.
- Recording whether a measure worked (`effective`) is published in `task_completed`.

---

### 3.11 F11 · Plan from Ground, backend · 4 h · P1

**Goal:** that mission control schedules tasks with versioned plans and the ship applies them idempotently, keeping the last plan if the link drops (option B).

**Depends on:** F9. **B builds** the mission control panel.

**Contracts**

| Direction | Contract |
| --- | --- |
| In | `POST /api/v1/groundlink/inbound/plans` (R9), idempotent by `batch_id` and `plan_version` |
| Publishes | `groundlink.ground_plan_received`, `engagement.ground_plan_applied` |
| GraphQL (`ground` role) | `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |
| Reads | Missions' `TaskStatusQuery`, filtered by consent |

**Tasks**

- [x] **11.1 Schema (0.75 h):** *(B-022: `inbound_plan`, `ground_plan`, `ground_item` and `link_state`)* `inbound_plan` (with unique `batch_id` and `plan_version`, hash and status), `ground_plan` and `ground_template` (Ground side, only in the Ground deployment or in the demo).
- [x] **11.2 Reception (0.75 h):** *(B-022)* R9 validates version and integrity (hash). Lower or repeated version: ignored. Corrupt plan: rejected entirely with a reason. Answers `202` and publishes `ground_plan_received`.
- [x] **11.3 Application in Missions (1.25 h):** *(B-022)* one transaction. Creates, updates and cancels templates with `GROUND` origin. An invalid item (nonexistent zone or assignee) is rejected on its own, with a reason, and the rest is applied. Publishes `ground_plan_applied` with what was applied and what was rejected.
- [x] **11.4 Ground side and simulated link (1 h):** *(B-022: `groundControl`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan`, `setGroundLink` and R5; without consent filtering or authentication of the `ground` role)* draft and publish GraphQL. Simulated `GroundLink` adapter with configurable delay and cut.
- [x] **11.5 Conflict rules (0.25 h):** *(B-022: all eight rules have a test)* one test for each of the rules in section 13.11 of the plan.

**Conflict rules (summary)**

| Situation | Rule |
| --- | --- |
| v12 arrives and v11 was already applied | One transaction. What was completed today is not touched. Changes apply to future instances |
| Lower or repeated version | Ignored (idempotent) |
| Corrupt plan | Rejected entirely with a reason and the previous one is kept |
| An invalid item | Only that item is rejected |
| Ground cancels something already completed | It stays completed. The cancellation applies to the future |
| The crew cannot do a Ground task | It is blocked with a reason and not deleted |
| The link drops | The last plan continues. Own tasks keep being created |
| Incident tasks | They are local and prevail. Ground does not delete them |

**Acceptance criteria**

- With the link cut, the plan stays queued and on return it arrives, is applied and is confirmed.
- Delivering the same plan twice leaves the tasks only once.
- What the crew completed or created is not lost when a plan is applied.

**Milestone:** I7 (hour 32, together with B's interface).

---

### 3.12 F15 · Ground link and consent · 3 h · P2

**Goal:** that Ground receives, on reconnect, only what the crew authorized and in order.

**Contracts**

| Direction | Contract |
| --- | --- |
| Consumes | `monitoring.alert_*`, `facility.incident_*`, `engagement.task_completed · task_created · task_blocked · ground_plan_applied`, `knowledge.recommendation_ready`, `crew.consent_changed`. Reads `ConsentQuery` |
| Publishes | `groundlink.link_state_changed`, `groundlink.batch_acknowledged` |
| API | `PUT /api/v1/groundlink/link` (R5), `groundLinkStatus`, `syncGroundLinkNow` |

**Tasks**

- [ ] **15.1 Schema (0.5 h):** `link_state`, `outbound_batch`, `outbound_item` (states `queued`, `sent`, `acked`, `withheld`).
- [ ] **15.2 Queue and consent filter (1 h):** every relevant event is queued. If its category is not shared it stays `withheld`. Without a link it only queues and nothing fails.
- [ ] **15.3 Batches and synchronization (1 h):** when the link returns a batch is built in order of occurrence, without what is `withheld`. Idempotent per batch. Confirmation from Ground with delay.
- [ ] **15.4 API and link state (0.5 h):** R5 simulates the cut and the return. `groundLinkStatus` reports queue, last sync and state. Publishes `link_state_changed`.

**Acceptance criteria**

- Nothing is uploaded without the consent of its category.
- The queue survives a restart of the machine.
- Resending an already confirmed batch does not duplicate anything.

---

## 4. Design of A's modules

### 4.1 Events

**Those A publishes (19):**

| Event | Receivers |
| --- | --- |
| `telemetry.readings_recorded` | Monitoring, Gateway |
| `telemetry.scenario_changed` | Gateway |
| `monitoring.alert_raised` | Knowledge (B), Missions, Gateway, Link, Facility |
| `monitoring.alert_acknowledged` | Missions, Gateway, Link |
| `monitoring.alert_resolved` | Missions, Gateway, Link, Facility |
| `engagement.task_assigned` | Gateway |
| `engagement.task_completed` | Gateway, Link |
| `engagement.task_created` | Gateway, Link |
| `engagement.task_blocked` | Gateway, Link |
| `engagement.ground_plan_applied` | Link, Gateway |
| `crew.baseline_updated` | Monitoring |
| `crew.consent_changed` | Link |
| `groundlink.link_state_changed` | Gateway |
| `groundlink.batch_acknowledged` | Gateway |
| `groundlink.ground_plan_received` | Missions, Gateway |
| `facility.incident_opened` | Missions, Gateway, Link |
| `facility.incident_updated` | Gateway, Link |
| `facility.incident_resolved` | Missions, Gateway, Link |
| `facility.zone_status_changed` | Gateway |

**Those A receives from B (3):** `knowledge.recommendation_ready` (Missions, Gateway and Link), `knowledge.recommendation_enriched` (Gateway) and `assistant.answer_ready` (Gateway).

### 4.2 Synchronous reads between A's modules

| Reader | From whom | Facade |
| --- | --- | --- |
| Monitoring | Telemetry | `ReadingQuery` |
| Monitoring | Crew | `BaselineQuery` |
| Facility | Monitoring | `ActiveAlertsQuery` |
| Missions | Facility | `ZoneQuery` |
| Link | Crew | `ConsentQuery` |
| Link | Missions | `TaskStatusQuery` |

**With B:** Missions reads `ActionCatalogQuery` (B). B reads `RuleQuery` and `ActiveAlertsQuery` (A).

### 4.3 Map of events to WebSocket messages

| Domain event | WebSocket message |
| --- | --- |
| `telemetry.readings_recorded` | `telemetry.tick` (coalesced to 1 Hz) |
| `telemetry.scenario_changed` | `scenario.changed` |
| `monitoring.alert_raised · acknowledged · resolved` | `alert.raised · alert.updated · alert.resolved` |
| `knowledge.recommendation_ready · enriched` | `recommendation.ready · recommendation.enriched` |
| `engagement.task_assigned` | `task.assigned` (and `reminder.due` from the scheduler) |
| `facility.incident_opened · updated · resolved` | `incident.opened · incident.updated · incident.resolved` |
| `facility.zone_status_changed` | `zone.status` |
| `groundlink.link_state_changed` | `groundlink.state` |
| `groundlink.ground_plan_received`, `engagement.ground_plan_applied` | `plan.received · plan.applied` |
| `assistant.answer_ready` (and the transcript) | `assistant.transcript · assistant.token · assistant.answer` |
| (the channel's own) | `subscribe · unsubscribe · resume · ping · pong` |

### 4.4 Flow of a per-zone alert

1. The reading comes in through R1 and `telemetry` stores readings and `readings_recorded` in one transaction.
2. The relay delivers the event to Monitoring, which evaluates the catalog per zone.
3. If a rule fires, Monitoring stores the alert and `alert_raised` in one transaction.
4. In parallel the event is received by: Gateway (pushes it over WebSocket), B's Knowledge (builds the recommendation), Facility (opens the ticket), Missions (creates tasks) and Link (queues it).
5. Facility publishes `incident_opened` and `zone_status_changed`. Gateway pushes them.
6. The crew acknowledges through GraphQL and `alert_acknowledged` is published.

### 4.5 Data schemas

The complete tables of each schema are in section 7 of the plan. Common rules: one schema per module, no foreign keys between schemas, `evidence_state` and `origin` mandatory where applicable and one Alembic migration per module with its own version table.

---

## 5. Contracts A delivers to B

### 5.1 REST (7)

| ID | Route | Use |
| --- | --- | --- |
| R1 | `POST /api/v1/telemetry/readings` | Batches of readings |
| R4 | `POST /api/v1/sim/scenarios/{key}:start · :stop` | Demo scenarios |
| R5 | `PUT /api/v1/groundlink/link` | Cut or restore the link |
| R6 | `GET /api/v1/rules/catalog.json` | Rule catalog |
| R7 | `GET /health · GET /ready` | Health (**done**) |
| R8 | `POST /api/v1/admin/outbox/{id}:replay` | Requeue a dead event |
| R9 | `POST /api/v1/groundlink/inbound/plans` | Plan from Ground |

### 5.2 GraphQL (31 operations from A)

| Module | Operations |
| --- | --- |
| Monitoring | `dashboard`, `alerts`, `alert`, `rules`, `acknowledgeAlert` |
| Telemetry | `readings`, `zoneReadings` |
| Facility | `ship`, `incidents`, `incident`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| Crew | `crewMember`, `setConsent`, `recordBaseline` |
| Missions | `tasks`, `groundPlan`, `completeTask`, `snoozeReminder`, `createTask`, `updateTask · deleteTask`, `blockTask` |
| Link | `groundLinkStatus`, `syncGroundLinkNow`, `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |
| Platform | `outboxStats` |

### 5.3 WebSocket (14 messages)

`telemetry.tick`, `alert.*`, `recommendation.*`, `task.assigned · reminder.due`, `assistant.transcript`, `assistant.token · answer`, `groundlink.state`, `incident.*`, `zone.status`, `plan.received · applied`, `scenario.changed`, `subscribe · unsubscribe`, `resume`, `ping · pong`.

Server message: `{ "seq": 18342, "topic": "alerts", "type": "alert.raised", "at": "…", "data": { … } }`.

---

## 6. Quality and tests

### 6.1 Matrix

| Level | What it covers | Tool |
| --- | --- | --- |
| Domain | Pure functions for PIO₂, windows, rules engine, anomalies, lifecycle | pytest, Hypothesis |
| Contract | Each event against its model. Stable GraphQL schema and WebSocket messages | pytest, schema generation and comparison |
| Architecture | Import rules between modules and layers | import-linter and its canaries |
| Integration | Outbox, relay, migrations, handlers, GraphQL and WebSocket against real PostgreSQL | testcontainers |
| End to end | Scenario → alert → ticket → WebSocket → acknowledge → normalize → resolve | pytest with a WebSocket client |
| Plan from Ground | Link cut, late arrival, repeated version, corrupt plan, invalid item | pytest, testcontainers |
| Offline | Container without network: full flow with the `jury` profile | Manual, on another computer |

### 6.2 Rules engine test vectors (mandatory)

| Input | Expected result |
| --- | --- |
| 760 mmHg, 21 % O₂ | PIO₂ ≈ 149.7 mmHg, normoxia, green |
| 760 mmHg, 18 % O₂ | PIO₂ ≈ 128.3 mmHg, yellow (below 145, above 127) |
| 56.5 kPa (423.8 mmHg), 34 % O₂ | PIO₂ ≈ 128.1 mmHg, yellow, close to 127 |
| 1 h average ppCO₂ = 3.1 mmHg | Red |
| 14.7 to 12.0 psia in 1 min (Δ 2.7 psi) | 2.7 psi/min, within 13.5. No rate alert |
| Drop of 14 psi in 0.5 min | 28 psi/min. Rapid depressurization alert |

### 6.3 Test rules

- Test first and watch it fail for the right reason.
- Integration tests use real PostgreSQL, not simulations.
- Each test is independent and prepares its own data.
- A test written after the code is marked as such in the evidence report.

---

## 7. Definition of done

One of A's phases is **done** when:

- [ ] It meets its acceptance criteria.
- [ ] `scripts/check.sh` ends green (ruff, strict mypy, import-linter, pytest with 80 % coverage or more).
- [ ] There is a reversible migration if there are new tables.
- [ ] Handlers are idempotent and have a duplicate test.
- [ ] Every rule value carries `evidence_state`, and what has no source says `DEMO`.
- [ ] It works without internet and without a ground link.
- [ ] If it touches a contract, B reviewed it beforehand.
- [ ] There is an evidence report in `docs/tdd/` for the block.
- [ ] The corresponding entry is in `logbook-dev-a.md`.

---

## 8. Risks specific to A

| Risk | Probability | Mitigation |
| --- | --- | --- |
| The hours for `crew` (baseline and consents) are not assigned to a phase | High | They are absorbed in F2 (baseline facade) and F15 (consent). If they are not enough, it is the first deviation: tell B and the user |
| A contract change breaks B's interface without warning | Medium | Schemas exported from F5 and types generated in B's CI. B's review before changing |
| The trend alert generates noise and false tickets | Medium | Minimum change per metric, minimum of 65 history points, and the trend only warns (it does not open a ticket) |
| Polling and `NOTIFY` do not reach the 1 s goal | Medium | `LISTEN/NOTIFY` already implemented. Measure before the demo and record the result |
| The relay becomes a bottleneck or loses order | Medium | A single worker ordered by id. Partition by `partition_key` only if needed. Order and duplicate tests |
| Corrupt, repeated or out-of-order Ground plan | Medium | Integrity hash, increasing version, atomic application and rejection with a reason |
| Conflicts between the Ground plan and local tasks without a link | High | Conflict rules tested one by one (section 3.11) |
| `reading` grows without control | Low | Partitioning by day and BRIN index. Configurable retention |
| With the real 1 h windows, Monitoring queries about 3,600 samples per metric and zone on each batch | Medium | Today it evaluates with raw readings. If it weighs too much, use `rollup_mean` (already exists) for the long windows. Measure before the demo |
| Milestone I2 depends on the gateway, which arrives in F5 | Medium | B continues with its recordings until I5. Recorded as an inconsistency of the plan |
| Lack of `make` and of a free port 5432 on other people's machines | Low | `scripts/check.sh` and `SPACEAPP_DB_PORT` |
| If A is absent, B does not know the core | Medium | Short README per module, TDD reports and contract tests as documentation |

---

## 9. Coordination with Dev B

**What A delivers to B**

1. **I0 (hour 1):** contracts, event registry and in-memory bus. **Ready for review.**
2. **I1 (hour 4):** real outbox. **Available.**
3. **I2 to I5:** real per-zone readings, incidents and gateway, so that B removes its mocks.
4. **F5:** `schema.graphql`, OpenAPI and `ws-messages.schema.json` to generate types and mocks.
5. `alert_raised` with `zone_id` and the `RuleQuery` and `ActiveAlertsQuery` facades.

**What A needs from B**

1. `recommendation_ready` and the `ActionCatalogQuery` facade (Missions uses them).
2. `assistant.answer_ready` so that the gateway turns it into WebSocket messages.
3. The Knowledge and Assistant resolvers, to compose the schema.

**When to notify**

- If a contract needs a new field: **before** implementing it, with a request to the owner.
- When finishing each phase: one line with what is ready and what is missing.
- When detecting that one of B's mocks does not reflect the real behavior.

**Pending for the first meeting with B:** review the in-memory bus, the handler signature (`HandlerContext`) and the event registry.

---

## 10. Pending decisions that affect A

They are not decided without consulting. Meanwhile the indicated assumption is used.

| # | Decision | Current assumption |
| --- | --- | --- |
| 1 | ~~A severity escalation event is missing.~~ **Resolved in F2:** each rule has a fixed severity and going up a level means resolving the mild alert and raising the serious one, so `monitoring.alert_escalated` is not needed. It remains to agree with B whether the gateway maps `alert.updated` to the acknowledgement | No new event |
| 2 | Name of the profile variable and default value | `SPACEAPP_PROFILE` with `jury` |
| 3 | Authenticity of the Ground plan | Integrity hash only. The cryptographic signature remains as an improvement |
| 4 | Scope of the Ground panel | The same SPA with the `ground` role and a simulated link |
| 5 | What Ground shares by default | "Tasks" category on by default |
| 6 | Radiation rules (level 2 of the context document) | Outside F2. The radiation `AUTO` types remain as pending rules |
| 7 | Thresholds for heart rate, blood pressure and SpO₂ | `DEMO` until there is a citable source (for example NEWS2, unverified) |
| 8 | Real users for `CODEOWNERS` | `@dev-a` and `@dev-b` placeholders |
| 9 | Demo scenario (transit to Mars, lunar base or ISS) | Transit ship. Changing it means changing data |

---

## 11. Master checklist for Dev A

**P0 cut (21.5 h): 11 h done**

- [x] F0 · Foundations: contracts, in-memory bus, profiles and architecture (I0, in B's review)
- [x] F1 · Outbox, relay, inbox and `/ready` (I1)
- [x] F2 · Rule catalog, engine with the six vectors, anomalies and alerts
- [x] F3 · Batch ingestion, simulator with per-zone scenarios and rollup (I2, simulator side)
- [ ] F4 · Floor plan, catalog of 61 types, automatic and manual tickets, zone status (I3)
- [ ] F5 · Composed GraphQL schema, `/ws` gateway, exported contracts (I5)
- [ ] F9 · Dockerfile, compose and test without internet (I6)

**P1 and P2 (9.5 h)**

- [ ] F10 · Templates, tasks with origin and own tasks
- [ ] F11 · Plan from Ground, application with conflict rules (I7)
- [ ] F15 · Queue toward Ground with consent and synchronization

**Closing**

- [ ] Short README per module
- [ ] Evidence report for each block in `docs/tdd/`
- [ ] Entry for each block in `logbook-dev-a.md`
- [ ] Final test on another computer, without internet, with the `jury` profile
