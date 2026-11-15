# SYRA · Health monitor for astronauts

NASA International Space Apps Challenge 2026 · Theme: *The Next Frontier* · Challenge: **Create Health
Monitoring Software for Astronauts on Space Missions**

> **Decision-support prototype. Not a medical device.** Every figure without a verified source is labeled
> `DEMO`, every body measurement is simulated, and nothing here replaces a flight surgeon.

## What it is

SYRA (Spaceflight sYstem for Remote Assessment) is a health and habitat monitor for a crew on a long mission. It reads the habitat's sensors, checks
them against rules that cite their source, raises alerts with a probable cause and a recommended action, tracks
the crew's daily health routines, and lets the astronaut ask questions that are answered only from loaded
documents. It is built so that **it keeps working on board with no link to Earth**.

The user is the astronaut. Mission control (Ground) is secondary: it prepares versioned task plans that reach the
ship over a delayed link and are kept in a local copy.

## The problem

Long missions expose people to radiation, isolation and confinement, distance from Earth, altered gravity and a
hostile closed environment (the five hazards of NASA's Human Research Program). Signals take 3 to 22 minutes each
way between Mars and Earth, so the crew must be able to assess their own state and act without waiting. Public
in-flight vital-sign data is almost nonexistent, which means a prototype has to simulate, say so, and be strict
about what has a source and what does not.

## Objective

Build software that gathers health indicators and lets astronauts assess their state and act on it, with three
commitments:

1. **Autonomy.** The core (readings, rules, alerts, tasks, recommendations) runs on board without internet, a
   language model or Ground.
2. **Traceability.** Every threshold and every recommendation points to a document and a requirement, or says
   plainly that it is a demonstration value.
3. **Honesty.** The system does not invent protocols, states or measurements.

## What it covers

| Area | What it does | Status |
|---|---|---|
| **Habitat telemetry** | Simulated sensors in 10 zones (pressure, O₂, CO₂, temperature, humidity) at the sampling rates of NASA-STD-3001 V2 6001; five scenarios (`co2_slow`, `pressure_leak`, `humidity_high`, `o2_failure`, `heat`) | Working |
| **Rules and alerts** | 25 versioned rules with source and evidence state, O₂ and CO₂ judged by **partial pressure**, moving windows, trend detection, hysteresis, acknowledgement | Working |
| **Recommendations** | One per alert, with citations; labeled `DEMO` when it comes from demonstration data | Working |
| **Habitat map and incidents** | Floor plan with zone status, 61 incident types, tickets opened by alerts or reported by hand | Working |
| **Tasks** | Daily health and ship routines, crew-owned tasks, blocking with a reason, streak that rewards only health routines | Working |
| **Ground link** | Versioned plans with a hash, simulated delay and cut link, idempotent delivery, local copy on the ship | Working |
| **Knowledge (RAG)** | Search over NASA documents (BM25, optional `bge-m3` embeddings) with a demonstration catalog as fallback | Working; the PDFs are not in the repository |
| **Assistant** | Text and voice questions answered **in English**, only from loaded sources, with citations; template answer when no model is available | Working; Ollama and n8n are optional |
| **Voice** | Whisper speech-to-text with an editable transcript and confirmation, Kokoro text-to-speech | Working in Docker |
| **Crew** | Who is on board (name, role, portrait) | Working; **no health data** (see below) |
| **Web console** | Mission overview, crew, ship environment, tasks, assistant, Ground control, settings; demo mode and real-backend mode | Working |

### What it does not do

- **No wearable data.** There are no heart rate, blood pressure, SpO₂ or radiation sources. The crew endpoint
  returns an unknown state (`null`) and no vitals; the console says "No wearable data" instead of "Nominal".
- **No personal sessions yet.** They need identity, which does not exist. Consent and personal-baseline changes
  are not in the backend (the console refuses them with an explicit message).
- **No Alexa.** It appears only as a profile name; it is not implemented (and it would not be autonomous).
- **No medical advice.** The language model explains; it never decides an alert and never blocks one.

## How it is built

A **modular monolith with hexagonal modules**: one process, one deployment, boundaries enforced in CI by
`import-linter`.

```
 sensors / simulator ──► telemetry ──┐
                                     ├─► outbox (PostgreSQL) ─► monitoring ─► alerts ─┬─► knowledge ─► recommendation
 Ground plans ───────► groundlink ───┘                                                ├─► facility (zones, incidents)
                                                                                      └─► engagement (tasks)
 React console ◄── GraphQL (reads, commands) · REST (machines) · WebSocket /ws (everything pushed)
```

- **Events:** state and event are written in one transaction (outbox); a relay delivers at least once, and each
  handler is idempotent. No Kafka, no Redis.
- **Interfaces:** GraphQL for the console, REST for machine commands (readings, simulator, Ground link, crew
  directory, voice), WebSocket for server push. No GraphQL subscriptions.
- **Data:** one PostgreSQL schema per module, no foreign keys across schemas; modules read each other only
  through their `contracts` and `facade`.
- **Rules as data:** thresholds live in `rules/catalog/monitoring.json` with requirement, document and evidence
  state; the engine is pure code. Of the 25 rules, 8 are `VERIFIED` against NASA-STD-3001, 1 comes from a
  Technical Brief (`TB`) and 16 are `DEMO`.
- **Stack:** Python 3.12, FastAPI, Strawberry GraphQL, SQLAlchemy async, asyncpg, Alembic, PostgreSQL 16 with
  pgvector, Pydantic v2; React, Vite, TypeScript, urql; Whisper, Kokoro and Ollama in Docker; n8n for the
  assistant workflow.

| Module | Responsibility |
|---|---|
| `telemetry` | Sensors, readings, rollups, simulator and scenarios |
| `monitoring` | Rules, windows, anomalies, alerts and their lifecycle |
| `knowledge` | Documents, passages, actions, recommendations |
| `assistant` | Questions by text or voice, grounded answers, citations |
| `crew` | Who is on board |
| `facility` | Habitat, zones, floor plan, incidents |
| `engagement` | Daily tasks, templates, streak |
| `groundlink` | Ground plans, link state, local copy on the ship |
| `realtime` | WebSocket gateway |

## Evidence and honesty rules

1. The language model never decides an alert; it only explains. A missing model never delays one.
2. A figure without a verified source is labeled `DEMO`; body data is also labeled *simulated*.
3. The banner "Decision-support prototype. Not a medical device" is always visible.
4. Color is never alone: every state has a shape, an icon and text (● Nominal, ▲ Attention, ◆ High, ■ Critical).
5. No medical protocol is invented. With no supporting passage the assistant says *"I don't have that
   information in the loaded sources."*
6. Nothing runs by voice until the transcript is confirmed; text input is always there. An emergency never
   depends on the astronaut speaking: alerts come from sensors.
7. O₂ and CO₂ are judged by partial pressure (`PIO₂ = (P_total − 47 mmHg) × fraction_O₂`), and the console shows
   what the backend computes instead of recalculating it.

## Quick start

Requirements: Python 3.12 (managed by `uv`), Node 22.18+, Docker.

```bash
uv sync                                    # Python dependencies
scripts/dev-backend.sh                     # PostgreSQL (:5434), migrations, API on :8002 with the simulator
cd web && npm install && npm run dev:backend   # the console against the real backend (http://localhost:5173)
```

`npm run dev` runs the console in **demo mode** with labeled fixtures and no backend. The browser only talks to
the Vite origin, which proxies `/graphql`, `/ws` and `/api` to `SPACEAPP_API_PROXY` (default
`http://127.0.0.1:8002`), so CORS is not needed. For another API port:
`SPACEAPP_API_PORT=8010 scripts/dev-backend.sh` and `SPACEAPP_API_PROXY=http://127.0.0.1:8010 npm run dev:backend`.

### A seeded mission

```bash
SPACEAPP_DATABASE_URL=postgresql+asyncpg://spaceapp:spaceapp@localhost:5434/spaceapp \
  uv run python -m spaceapp.devtools.seed_mission --reset          # about 40 s
SPACEAPP_SIMULATOR_AUTOSTART=false scripts/dev-backend.sh            # keeps that state on screen
```

The seed replays three hours of simulated telemetry through the app's own use cases, so the modules write
everything: the habitat map, readings of every zone, a slow CO₂ drift in the laboratory that the rules turn into
the `env-co2-1h` alert with its recommendation, the incident it opens, a second incident reported by hand, the
day's tasks, a confirmed Ground plan and the crew roster (`data/crew/roster.json`). `--reset` empties the module
tables first; without it the seed refuses to run over existing readings.

To watch a live anomaly instead, leave the simulator on and trigger one:

```bash
curl -X POST localhost:8002/api/v1/sim/scenarios/co2_slow:start -H 'content-type: application/json' -d '{"zone":"lab"}'
```

`SPACEAPP_RULE_WINDOW_SCALE=0.0167` (the script default) shortens the one-hour rule windows to about a minute for
demonstrations; with `1.0` the standard's values apply. The profile is `SPACEAPP_PROFILE` (`dev1`, `dev2` or
`jury`, the default); the database port is `SPACEAPP_DB_PORT`.

### Optional services

| Service | How | Without it |
|---|---|---|
| Assistant dev server | `python -m spaceapp.devtools.assistant_server` (port 8000) | The assistant tab uses a labeled local simulation |
| Ollama (assistant model) | `docker/ollama/README.md` | Template answers from the cited passages |
| n8n workflow | `n8n/README.md` | The backend answers without the orchestrator |
| Voice (Whisper, Kokoro) | `docker/voice/README.md` | Type the question instead |
| NASA PDFs and index | `src/spaceapp/modules/knowledge/README.md` | Demonstration catalog |

## Tests and quality

```bash
scripts/check.sh                                  # ruff, mypy (strict), import-linter and pytest with coverage
PATH="$PWD/.venv/bin:$PATH" uv run pytest -q     # integration tests start PostgreSQL with testcontainers (Docker)
cd web && npm test && npx tsc --noEmit && npx eslint .
```

At the time of writing: 1,028 Python tests (integration included) and 307 web tests pass. The suite includes
contract tests: the console's GraphQL operations are validated against the backend's exported schema.

## Repository layout

```
src/spaceapp/         backend: modules/, platform/ (outbox, bus, profiles), interfaces/, devtools/
migrations/           one Alembic environment per module
rules/                monitoring rule catalog (with sources and evidence states)
data/                 facility plan, incident types, task templates, crew roster, knowledge catalog, simulator layout
web/                  React console (demo and backend modes)
contracts/            exported GraphQL schema, OpenAPI and WebSocket message schemas
docker/  n8n/         Compose files, voice and Ollama images, assistant workflow
docs/                 architecture plan, front spec, challenge notes, task plans, TDD evidence
logbook-dev-*.md      what was done, how, with what evidence
```

## Documentation

- `docs/architecture-plan.md`: architecture, ADRs, channels, phases.
- `docs/spaceapps-challenge-notes.md` and `docs/spaceapps-health-monitor-context.md`: the challenge, analysis and
  competition.
- `docs/front-spec.md` and `docs/FRONTEND_INTEGRATION.md`: console specification and backend integration.
- `src/spaceapp/modules/knowledge/README.md` and `src/spaceapp/modules/assistant/README.md`: RAG, evaluation and
  assistant details.
- `logbook-dev-a.md` and `logbook-dev-b.md`: the engineering logbooks, including what was *not* verified.

## Sources

NASA-STD-3001 Volumes 1 and 2 (Rev F), the OCHMO Technical Briefs (TB-002, TB-003, TB-004, TB-044), the Human
Integration Design Handbook and NASA's Human Research Program hazards. The NASA PDFs are **not redistributed**:
their license status is recorded in `data/knowledge/manifest.json` and they are indexed locally only. Crew names,
roles and portraits are fictional and illustrative.

## Team

Built during the 48 hours of Space Apps 2026 by two developers: Dev A (platform, telemetry, rules, facility,
engagement, Ground link, GraphQL and WebSocket) and Dev B (knowledge, assistant, voice and the web console).

## License

No license has been chosen yet.
