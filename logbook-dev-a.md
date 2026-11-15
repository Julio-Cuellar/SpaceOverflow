# Project logbook

> NASA Space Apps 2026 · health monitor for astronauts
> Chronological record of what is done and of every change made, including those made **outside the repository** (installations, services) and the errors that were fixed.
> Last updated: November 15, 2026, 09:30.

## How this logbook is maintained

- Each block of work adds **a new entry at the end** of section 3, before closing.
- An entry has: what was done, files created or changed, how it was verified and with what result, decisions and pending items.
- Errors are recorded as they happened, with their fix. They are written in section 6 and referenced from the entry.
- What is done on the user's machine (installing, starting services, downloading) is noted in section 5. It is never left unrecorded.
- The hours of the milestones are work hours per person, not clock hours. The clock hours in this logbook come from the files' modification dates.

### Entry template

```markdown
### B-0XX · Short title
- **What:** …
- **Files:** …
- **Verification:** command → result
- **Decisions:** …
- **Pending:** …
```

---

## 1. Current status

| Area | Status |
| --- | --- |
| Architecture plan | Drafted and **pending confirmation** by the user |
| Split between two developers | Drafted (section 16 of the plan) and detailed for Dev B |
| Dev A's detailed plan | `docs/tasks-dev-a.md` (F0 and F1 marked as done) |
| Plan and artifact generator | In the repository (`tools/docgen/`), with a test that verifies it reproduces the document |
| Code | **Dev A's Blocks 1 and 2 finished** (F0 to F3). **F4, F5, F10 and F11 finished** on the backend side (minor pending items: DataLoaders, cost limit, consent and Crew). F9 is left for when the interface is ready (user's decision). Dev B's work (F0, F6 to F8, F12, F13) is already integrated from `testing` |
| Tests | **711 pass and 19 are skipped** (the skipped ones are Dev B's), 95.90 % coverage, ruff and strict mypy with no errors, 4 architecture contracts kept |
| Interactive artifact | Version 4 published: https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8 |
| Git repository | The work lives in `~/Documentos/SpaceOverflow`, branch `dev-A`. **Pushed to GitHub** (B-021): merges B-015 and B-016, F5, 5.4 and F4. The PR to `testing` is missing |
| Proposed next block | PRs `dev-A → testing` and `dev-B → testing`; integrate in `testing` (assistant in `main.py`, front-end proxy); then `main` and F9 (B-025) |

---

## 2. Decisions

### 2.1 Made by the user

| Decision | Where it ended up |
| --- | --- |
| Challenge: health monitoring for astronauts | Project context |
| Autonomous operation, without a ground link | Context, plan section 1 |
| Python with FastAPI, PostgreSQL, GraphQL and WebSockets | Plan section 4 |
| Hexagonal architecture as a modular monolith with event bus and outbox | Plan sections 5 and 6 |
| Ship panel with floor plan, incident tickets and gases per zone | Plan 13.7 |
| Daily crew tasks: health, ship and incidents | Plan 13.8 |
| Catalog of incident types in the plan and the artifact | Plan 13.9 |
| **Option B:** mission control schedules tasks with versioned plans, and the crew creates their own | Plan 13.11 |
| Split the plan between two developers, with **the whole RAG in only one** | Plan section 16 |
| Execute Dev A's plan starting with Block 1 | Entry B-008 |

### 2.2 My assumptions (the user has not confirmed them)

| Assumption | Why | Effect if it changes |
| --- | --- | --- |
| Interface with React, Vite and TypeScript | No front end was indicated. It was answered that it was the most convenient | Only `web/` changes |
| Variable `SPACEAPP_PROFILE` with `jury` by default | It works without internet or Alexa | A change in `config.py` |
| Authentication by selecting a local profile | No external accounts | Affects the Ground panel |
| n8n as an optional Ollama adapter | Saves one piece in 48 h | Affects `LlmGateway` |
| Python 3.12 with `uv` instead of the system's 3.14 | Avoids unavailable binary wheels | None if 3.12 is kept |
| Development database on port 5433 | Port 5432 is used by another of the user's projects | Variable `SPACEAPP_DB_PORT` |
| 10 s window for the pressure rate-of-change rule (`env-dpdt`) | A real leak averages about 6 psi/min in 60 s and did not reach 13.5. The standard does not set the window | A change in the JSON catalog |
| Rule windows scalable with `rule_window_scale` (1.0 by default) | A 1 h window makes the demonstration unworkable | Only the configuration changes |
| Relay and simulator off by default (`SPACEAPP_RELAY_ENABLED`, `SPACEAPP_SIMULATOR_AUTOSTART`) | With the simulator off the system starts anyway. In F9 they are enabled for the `jury` profile | The default value changes |
| "Tasks" consent category active by default | Ground needs to see the state of its tasks | The default consent changes |
| Catalog of 61 incident types as a proposal | There is no citable official list | Only the `VERIFIED` ones come from the standard |

### 2.3 Pending decisions

1. The RAG: does it only return passages with a citation or does it also write with Ollama?
2. Does n8n remain the orchestrator or is Ollama called directly?
3. Is F12 (full RAG) raised to P0? It fits in Dev B's slack before delivery.
4. Local embeddings model (today the search starts with full text).
5. Authenticity of the Ground plan: hash only or cryptographic signature.
6. Scope of the Ground panel: same SPA with a `ground` role or a separate deployment.
7. Demo scenario (Mars transit, lunar base or ISS), language for the jury and team size.
8. Real users for `CODEOWNERS`.

---

## 3. Chronological record

### B-001 · Loading the context
- **What:** the two documents in `docs/` were read (the consolidated context and the Notion export) and the project status was summarized.
- **Files:** none modified.
- **Finding:** in Notion several documents appear as "Not opened" although they were already read. The consolidated context has the real status.

### B-002 · Architecture plan, first version
- **What:** hexagonal architecture plan with modular monolith and event bus with outbox. It includes ER, sequence and module-communication diagrams, and the table of channels and events (REST, GraphQL and WebSocket).
- **Files:** `docs/architecture-plan.md` (new). Artifact **version 1** (new).
- **Method:** the document and the artifact are generated from the same data source (see section 7) so they do not contradict each other.
- **Verification:** the artifact was opened in the built-in browser and showed no console errors.

### B-003 · Artifact version 2
- **What (at the user's request):**
  - relationships visible in the ER diagram, with lines and cardinality,
  - colors per participant in the sequence diagrams,
  - human body with 6 indicators in the cabin panel,
  - ship panel: floor plan of 10 zones, tickets, gas charts per zone and anomaly alerts,
  - daily health, ship and incident tasks.
- **Architecture changes:** new `facility` module (ship and incidents), 4 new events and tables `habitat`, `zone`, `incident` and `incident_update`.
- **Verification:** test of a pressure leak scenario in the browser (the zone was painted and the ticket was opened) and 40 relationship lines in the ER without invalid values.

### B-004 · Incident catalog and option B (artifact version 3)
- **What:**
  - catalog of 61 incident types in 12 categories, with a report form by category and type,
  - task plan from Ground (option B) with mission control panel, conflict rules and the crew's own tasks,
  - 4 events, 9 GraphQL operations, 1 REST route, 1 WebSocket message and 5 new tables.
- **Rename:** the `uplink` module became `groundlink` (see error E-2 in section 6).
- **Verification:** full flow in the browser (cut the link, publish, restore, apply, own task, block) and the plan's three test cases (corrupt, repeated, invalid item).

### B-005 · Split between two developers (artifact version 4)
- **What:** section 16 of the plan. Dev A takes the core and real time (31 h). Dev B takes the interface, Knowledge and the whole RAG (34 h, of which 15 h are RAG). It includes timeline, 8 integration milestones, cross contracts and rules to avoid blocking each other.
- **Correction:** the P0 cut is **40 h** (21.5 h A and 18.5 h B), not 41 h as was said before (error E-1).
- **Verification:** the planner computed the work queues and the milestones. It was checked that the hours per phase add up to the total.

### B-006 · Dev B's task document
- **What:** document with all of Dev B's tasks per phase, with subtasks and estimates, acceptance criteria, contracts, schemas, tests, risks and checklist.
- **Files:** `docs/tasks-dev-b.md` (new).
- **Verification:** the hours of each phase's subtasks add up to its total (34 h) and the contracts were checked against the plan's data.

### B-007 · Dev A's execution plan
- **What:** inline plan with the 4 work blocks, the files to create and the risks. The machine was reviewed before planning.
- **Machine findings:** no repository or code, system Python 3.14.4 (the plan asks for 3.12), no `pip` or `uv`, Docker with the daemon off, no PostgreSQL or Node.
- **Files:** none (conversation only).

### B-008 · Execution of Dev A's Block 1: F0 and F1
- **What:** implementation with TDD (test first, RED, minimal code, GREEN, refactor).
- **New files (45 Python modules, 80 in `src/`, 17 in `tests/`):**

| Path | Contents |
| --- | --- |
| `pyproject.toml`, `uv.lock`, `.python-version` | Project with Python 3.12 and dependencies |
| `src/spaceapp/platform/` | `events.py`, `bus.py`, `profiles.py`, `config.py`, `vocab.py`, `db.py`, `migrate.py` |
| `src/spaceapp/platform/outbox/` | `publisher.py`, `uow.py`, `relay.py`, `stats.py` |
| `src/spaceapp/modules/<9 modules>/` | `contracts.py`, `facade.py` and packages `domain`, `application`, `ports`, `adapters` |
| `src/spaceapp/event_registry.py` | Registry of the 22 events |
| `src/spaceapp/main.py` | Composition root with `/health` and `/ready` |
| `migrations/platform/` | Outbox and inbox migration |
| `tests/` | 122 tests: unit, contract, architecture and integration |
| `docker/compose.yaml` | PostgreSQL with pgvector |
| `Makefile`, `scripts/check.sh` | Full verification |
| `CODEOWNERS`, `README.md`, `.gitignore` | Repository |

- **Verification** (`scripts/check.sh`):

| Check | Result |
| --- | --- |
| ruff | No errors |
| strict mypy | No errors in 80 files |
| import-linter | 4 contracts kept, 0 broken |
| pytest | 122 pass |
| Coverage | 98.99 % (required minimum 80 %) |
| Real test | `docker compose up`, migration from the command line, `/health` 200 and `/ready` 200 |

- **Documented RED:** 5 collection errors in F0 and 3 in F1, all from nonexistent modules.
- **Milestones it enables:** I0 (contracts ready for Dev B's review) and I1 (real outbox available).
- **Pending:** Block 2 (F2 and F3).

### B-009 · TDD evidence report
- **What:** report with the real REDs and GREENs, the incidents during the cycle, a table of 24 guarantees and the coverage gaps.
- **Files:** `docs/tdd/f0-f1.tdd.md` (new).
- **Verification:** the per-file counts were checked against `pytest --collect-only`. A first version had 4 wrong per-file figures and was fixed (they add up to 122).

### B-010 · This logbook
- **What:** complete record of what was done in the session, with changes outside the repository, errors and pending items.
- **Files:** `logbook-dev-a.md` (new).

### B-011 · Plan generator inside the repository
- **What:** the source of the plan and the artifact (previously in a temporary session folder) was moved to `tools/docgen/`. It was given a command line and a test that guarantees it reproduces the document.
- **Files:**
  - new: `tools/docgen/{data.py, build.py, template.md, page.html, README.md}` and `tests/unit/test_docgen.py`,
  - changed: `pyproject.toml` (ruff ignores `tools`) and `.gitignore` (ignores `tools/docgen/out/`).
- **Changes in `build.py`:** it stops using fixed paths and receives `--artifact-url`, `--template`, `--page`, `--out-md` and `--out-html`. An unknown marker in the template makes the generation fail and names it.
- **TDD:** first 3 tests (RED: `can't open file 'tools/docgen/build.py'`). Then the generator (GREEN, 3 pass). The third test of the first version was weak (it only checked `stderr == ""`) and was replaced by a real one (error E-11).
- **Verification:** the repository's generator reproduces `docs/architecture-plan.md` **byte for byte** (`diff` with no differences) and generates the page with no unresolved markers.
- **Decision:** `docs/architecture-plan.md` is not edited by hand. `data.py` or `template.md` is changed and it is regenerated.
- **Not done:** the artifact was not published again, because its content did not change.

### B-012 · Dev A's task document
- **What:** document equivalent to Dev B's, with A's 10 phases in detail (F0 and F1 marked as done), contracts, flow of an alert per zone, map of events to WebSocket messages, test vectors, risks, coordination and pending decisions.
- **Files:** `docs/tasks-dev-a.md` (new). `tools/docgen/template.md` (link to the two task documents in section 16.1) and `docs/architecture-plan.md` (regenerated with the tool).
- **Verification:** each phase's subtasks add up to its total (31 h). A first version had F2 at 4.25 h (error E-12) and was fixed. A's contracts were extracted from the plan's data: 7 REST routes, 31 GraphQL operations, 14 WebSocket messages and 19 published events.
- **Finding:** the plan defines the `alert.updated` message but there is no domain event that originates it. It was left as a pending decision for Dev A (section 10 of their document).
- **Final verification:** `scripts/check.sh` green with 125 tests and 98.99 % coverage.

### B-013 · Execution of Dev A's Block 2: F2 and F3
- **What:** monitoring with rule catalog, deterministic engine and alert lifecycle (F2), and telemetry with simulator, idempotent ingestion and rollup (F3). TDD throughout the block.
- **New files (168 more tests):**

| Path | Contents |
| --- | --- |
| `src/spaceapp/modules/monitoring/` | Domain (`units`, `physics`, `series`, `trend`, `rules`, `engine`, `lifecycle`), JSON catalog, SQL and in-memory repositories, `EvaluateReadings` handler, `acknowledge_alert`, facades, catalog endpoint |
| `src/spaceapp/modules/telemetry/` | Domain (`readings`, `simulator`, `layout`), ingestion, rollup, simulator service, SQL repository, `SqlReadingQuery`, REST R1 and R4 |
| `src/spaceapp/platform/ids.py`, `migrations_env.py` | Stable identifiers and shared Alembic environment |
| `rules/catalog/monitoring.json` | 25 rules (20 threshold and 5 trend) with source and evidence state |
| `data/telemetry/sim_layout.json` | The 10 simulated zones |
| `migrations/monitoring/`, `migrations/telemetry/` | Own migrations (rules and alerts; sensors, readings partitioned by day, rollup and scenarios) |
| `tests/unit/{monitoring,telemetry}/`, `tests/integration/{monitoring,telemetry}/` | The new tests |
| `docs/tdd/f2-f3.tdd.md` | Evidence report |

- **Changed files:** `src/spaceapp/main.py` (relay and simulator startup by configuration, routers), `src/spaceapp/platform/config.py` (new settings), `tests/conftest.py` (migrates and cleans the three schemas), `pyproject.toml` (ruff rules for SQL and tests), `tools/docgen/data.py` and `template.md` (data model), `docs/architecture-plan.md` (regenerated) and `docs/tasks-dev-a.md` (status and differences).
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 113 files, 4 architecture contracts kept, 293 tests, 97.53 % coverage.
- **Live test with the real clock:** 130 s normal → 1,930 readings and 0 alerts. CO₂ scenario in the laboratory → trend (ATTENTION), pre-alert (ATTENTION) and verified alert (ALERT, `VERIFIED`), only in that zone, no errors in the log and with the outbox empty.
- **Decisions:**
  - Each rule has a fixed severity. Raising the level is resolving the mild alert and raising the severe one, so **`monitoring.alert_escalated` is not needed** (the plan's pending decision is resolved).
  - Rule windows require the data to cover at least half of the window. Demo time is accelerated with `rule_window_scale`.
  - The trend detector and the pressure rate-of-change rule were adjusted based on what the simulator showed (see E-14 and E-15).
- **Differences from the plan:** the `crew.baseline_updated` handler and `BaselineQuery` were not done (there are no baseline-relative rules yet). Details in `docs/tasks-dev-a.md`, section 3.3.
- **Plan finding:** milestone I2 asks to connect the ticks over WebSocket, but the gateway is F5. I2 is met only in the simulator part.
- **Pending:** Block 3 (F4 and F5). Measure Monitoring's performance with the real 1 h windows.


### B-014 · Dev A's work brought into the SpaceOverflow repository (branch dev-A)
- **What:** `https://github.com/Julio-Cuellar/SpaceOverflow` was cloned into `~/Documentos/SpaceOverflow` and Dev A's work (F0 to F3) was copied there onto the `dev-A` branch, which already existed on the remote with only the first commit.
- **How:** the 192 files that `.gitignore` respects were copied (without `.venv`, caches or `.git`). The template's `README.md` (`# SpaceOverflow`) was replaced by the project's.
- **State of the remote when cloning:** `main` and `dev-A` only have the first commit; `dev-B` and `testing` already have Dev B's work (`pyproject.toml`, `.gitignore`, `src/spaceapp/__init__.py`, `.github/CODEOWNERS`, CI, etc.).
- **Warning:** Dev A and Dev B each created their own `pyproject.toml`, `.gitignore`, `README.md` and `src/spaceapp/__init__.py`. When the branches are joined there will be conflicts in those files and they must be resolved by hand.
- **Verification:** the copy was compared with the source (`diff -r`) and the commit was pushed afterwards with `git push origin dev-A` (`2d38c34..8ddbad7`). The tests were not run again in the clone (no code file changed).
- **Pending:** resolve the conflicts with `dev-B` when joining the branches.


### B-015 · Merge of `dev-B` into `dev-A` (local only)
- **What:** `origin/dev-B` (Dev B's F0, F6 to F8, F12 and F13, with the web interface) was brought into `dev-A` with `git merge`. `origin/test-B` already contains `dev-A` (PR #3), so it added nothing new to this merge. **Nothing was pushed**: the merge commit is only on the machine.
- **Result:** 115 of Dev B's files came in without conflict and there were 5 "add/add" conflicts, resolved as follows:

| File | Resolution |
| --- | --- |
| `pyproject.toml` | Dev A's is kept (hatchling, uv, lint rules and architecture contracts) and `pypdf>=5` is added, which Dev B's PDF ingestion needs |
| `.gitignore` | Union of both |
| `knowledge/contracts.py`, `assistant/contracts.py` | The events are registered `EventPayload`s (the event registry and its contract test require them). Dev B's local copy of `AlertRaised` is kept. `CitationDTO` becomes an alias of `platform.vocab.Citation` (same fields and states), so Dev B's code did not change |
| `knowledge/facade.py` | Dev B's (mine was only a skeleton) |

- **Other changes from the merge:**
  - `.github/workflows/ci.yml`: the Python job used `pip install -e ".[dev]"` and Python 3.14, which do not work with Dev A's `pyproject.toml`. It now uses `astral-sh/setup-uv`, `uv sync --frozen` and `scripts/check.sh` with Python 3.12. The web job was not touched. It is a shared file: Dev B must review it.
  - The root `CODEOWNERS` was deleted (`@dev-a`/`@dev-b` placeholders). The one in Dev B's `.github/` rules, which still has no Dev A folders.
- **Verification** (`scripts/check.sh` on the merged tree): ruff, strict mypy, import-linter and **388 tests** (293 from Dev A and 95 from Dev B) with 97.22 % coverage. The web part (`npm`) and the real CI on GitHub were not run.
- **Pending:** push the merge (to `dev-A` or through a PR to `testing`) when the user confirms; Dev B to review the CI; complete `CODEOWNERS` with Dev A's folders; test the web interface against the backend.


### B-016 · Merge of `origin/testing` into `dev-A` (local only)
- **What (user's request: "pull down what is in testing"):** `git fetch` and `git merge --no-ff origin/testing` on `dev-A`. `testing` brought PR #4 (`integration/a-b`): Dev B integrated `dev-A`, aligned the Knowledge and Assistant contracts with Dev A's, loaded guidance for the 25 Monitoring rules, made the Knowledge subscription to the bus and adjusted the CI to `uv`.
- **Before merging:** there was F5 work from an earlier session **with no commit or logbook entry**. It was backed up in the session's *scratchpad* (`wip-f5.diff` and `wip-f5-untracked.tgz`) and in `git stash` (message: "wip F5 realtime+graphql antes de fusionar testing", i.e. "wip F5 realtime+graphql before merging testing").
- **Conflicts (5), resolved with the `testing` version**, because Dev B had already integrated and tested them in PR #4:

| File | Resolution |
| --- | --- |
| `.github/workflows/ci.yml` | The one from `testing` (Python 3.12, `uv sync --frozen`, ruff, mypy, import-linter and pytest with coverage separately). Equivalent to `scripts/check.sh` |
| `.gitignore` | The one from `testing`: it already includes Dev A's entries |
| `pyproject.toml` | The one from `testing` (`pypdf` with a comment) |
| `knowledge/contracts.py`, `assistant/contracts.py` | Dev B's. There is no longer a local copy of `AlertRaised`: Knowledge reads Monitoring's contract |

- **Kept from B-015:** the root `CODEOWNERS` stays deleted (GitHub uses the one in `.github/`).
- **Verification** (`scripts/check.sh` on the merge): ruff, strict mypy, import-linter and **547 tests** (19 skipped, Dev B's), with 97.27 % coverage.
- **Nothing was pushed.** `dev-A` is left with two local merges not pushed (B-015 and B-016).

### B-017 · F5: GraphQL, `/ws` gateway and end-to-end test
- **What:** the F5 work was recovered from the *stash* (message domain, hub with bounded queue, `/ws` endpoint, numbering and replay from the outbox, and its 32 tests, which already passed) and the GraphQL part that was in RED was finished.
- **What was discarded from the earlier work:** my Knowledge-to-bus adapter (`KnowledgeEvents`), because Dev B made his own in `testing` (`register_knowledge` with `HandleAlertRaised`). `main.py` now uses Dev B's. My "skip rules without guidance" also went away: Dev B covers the 25 rules and an unknown rule retries.
- **New files:**

| Path | Contents |
| --- | --- |
| `src/spaceapp/interfaces/graphql/schema.py` | Strawberry schema: `dashboard`, `alerts` (cursor pagination, filter by status), `alert` (with rule and recommendation with citations), `rules`, `zoneReadings` (per minute or raw), `knowledgeSearch` and the `acknowledgeAlert` mutation with a success-and-error `union` (`NOT_FOUND`, `ALREADY_RESOLVED`). Depth limit 10 |
| `src/spaceapp/interfaces/graphql/dashboard.py` | Cabin vital signs, as a pure function |
| `src/spaceapp/interfaces/graphql/context.py` | Services each operation receives |
| `src/spaceapp/modules/realtime/...` | From the earlier work: `domain/messages.py`, `application/hub.py`, `adapters/inbound/{ws,events}.py`, `adapters/outbound/sql.py`, `OutboxReplay` port |
| `tests/unit/graphql/test_dashboard.py`, `tests/unit/wiring/test_alert_to_recommendation.py`, `tests/integration/test_end_to_end.py` | New or rewritten tests |

- **Changed files:** `main.py` (Dev B's Knowledge, `build_services`, hub subscribed to the bus, `/graphql` and `/ws`), `monitoring/facade.py` (`AlertReadQuery` and `RuleQuery.all`), `telemetry/facade.py` (`TelemetryViews`: latest value per sensor and series), `pyproject.toml` and `uv.lock` (`strawberry-graphql`), `config.py` (`knowledge_catalog_path`), `tests/integration/graphql/test_schema.py` (two expectations fixed, E-19 and E-20) and `docs/tasks-dev-a.md` (F5 status).
- **How a vital sign is computed:** without alerts it is the average of the zones and carries no zone. With alerts the worst one rules: its severity, its zone, that zone's value and the evidence of its rule. PIO₂ is derived from the pressure and the O₂. An N₂ alert (with no sign of its own) counts toward the global severity.
- **End-to-end test:** the real app with relay (LISTEN/NOTIFY), a client on `/ws` and a CO₂ scenario in the laboratory. The alert arrives with `seq`, is acknowledged through `/graphql` and `alert.updated` arrives. **Latency from the alert to the client: 47, 47 and 73 ms** in three runs (goal: 1 s). The slowest tick took between 0.17 and 0.27 s to process.
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 149 files, 4 architecture contracts kept, **604 tests** (19 skipped, Dev B's) and 96.96 % coverage.
- **TDD:** the wiring test was rewritten first and failed (RED: `cannot import name 'KnowledgeEvents'`). The GraphQL tests were already in RED from the earlier session (`No module named 'spaceapp.interfaces'`). Those of `dashboard.py` were written before the code, but **were not run in RED** before writing it.
- **Decisions:**
  - Severities and states come out in uppercase in GraphQL (`ALERT`, `ACKNOWLEDGED`), as in Dev B's contract.
  - The habitat can be requested by UUID or by code (`transit-ship`).
  - Actions are signed with a demonstration crew member (`DEMO_CREW_MEMBER`) until profile selection exists.
  - Recommendations live in memory (Dev B's `InMemoryRecommendations`): they are lost on restart. Persistence is Dev B's.
- **F5 pending:** 5.4 (export `schema.graphql`, OpenAPI and `ws-messages.schema.json`, R8, `outboxStats` and cleanup of events older than 24 h), server `ping` every 15 s, `habitat` and `crew` topics, DataLoaders and cost limit, and the Crew queries.
- **Contract with Dev B:** the real schema includes all of `contracts/schema.graphql` (checked by `test_contract_superset.py`). A change to that shared file needs Dev B's review.

### B-018 · F5, task 5.4: exported contracts and outbox operation
- **Previous commit:** the user asked for a commit of B-017. It ended up as `9bed3c0` on `dev-A`, **not pushed**.
- **What:**
  - **Contracts for Dev B:** `python -m spaceapp.interfaces.contracts_export` writes `contracts/schema.generated.graphql` (full schema), `contracts/openapi.json` (with the `dev1` profile, so R8 appears) and `contracts/ws-messages.schema.json` (the path that `web/src/data/ws/types.ts` already cites). With `--check` it fails if anything changed. A test requires the published files to match the code.
  - **Dev B's draft `contracts/schema.graphql` is not touched.** The user did not answer whether it should be replaced, so the option that overwrites nothing was taken. The subset test is still in force.
  - **R8** `POST /api/v1/admin/outbox/{id}:replay`: a `dead` event goes back to `pending` with zero attempts and the relay is notified. It answers 404 if it does not exist and 409 if it is not dead. Only in `dev1` and `dev2`.
  - **`outboxStats`** in GraphQL: pending, dead and age of the oldest. In `jury` it returns null.
  - **Cleanup:** the relay deletes `done` events older than 24 h every 10 min (`purge_done`). Dead and pending ones are not touched. The inbox is not cleaned: if it were, requeueing an old dead event would repeat consumers that had already processed it.
  - **Server `ping`** on `/ws` after 15 s without messages.
  - **Message catalog:** `SERVER_TYPES` (type → topic) and `SYSTEM_TYPES` in the realtime domain. The tests require that each translated event produce a type published on its topic and that every published type have an event that produces it.
- **New files:** `src/spaceapp/platform/outbox/admin.py`, `src/spaceapp/interfaces/rest/admin.py`, `src/spaceapp/interfaces/contracts_export.py`, `src/spaceapp/modules/realtime/adapters/inbound/ws_schema.py`, the three files in `contracts/`, `tests/integration/test_outbox_admin.py`, `tests/unit/realtime/test_ws_schema.py` and `tests/unit/test_contracts_export.py`.
- **Changed files:** `platform/outbox/{__init__,relay}.py`, `realtime/domain/messages.py`, `realtime/adapters/inbound/ws.py`, `interfaces/graphql/{context,schema}.py`, `main.py` and `tests/unit/realtime/test_ws_endpoint.py`.
- **TDD:** each part started in RED (`cannot import name 'purge_done'`, missing `ping_interval`, missing `ws_schema` and missing `contracts_export`). A test looked at `app.routes`, but this version of FastAPI does not flatten included routers. It was changed to use the OpenAPI routes.
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 154 files, 4 architecture contracts kept, **623 tests** (19 skipped, Dev B's) and 97.04 % coverage.
- **F5 pending** (depends on other phases): Crew queries (`crewMember`, `recordBaseline`, `setConsent`), `habitat` (F4) and `crew` topics, DataLoaders and cost limit.

### B-019 · F4: ship, zones and incidents
- **Previous commit:** 5.4 ended up as `81686a1` (not pushed).
- **What:** an alert of ALERT severity or higher in a zone opens a ticket with type, description, severity and location, and the zone takes its color in the same transaction. GraphQL, WebSocket and contracts included.
- **Data (generated once from `tools/docgen`):**
  - `data/facility/plan.json`: the 10 zones, with the same codes as the simulator and the artifact's geometry. All `DEMO`.
  - `data/facility/incident_types.json`: 61 types and 12 categories. Each AUTO type carries its **exact rule keys**. In `ITYPES` there were families (`env-pio2` applied to hypoxia and to hyperoxia). The 20 rules that do not exist yet go in `pending_rules`.
- **Domain rules** (`facility/domain/incidents.py`, pure functions): ATTENTION does not open a ticket. There is a single open automatic ticket per zone: if another alert arrives it is noted and, if it is worse, it is escalated (`incident_updated`). When the last alert is resolved, the ticket is marked "values normal" but **does not close itself**. An automatic ticket cannot be closed with active alerts in its zone; a manual one can. The zone's color is the worst severity among active alerts and open tickets, and it is only published when it changes.
- **Persistence:** migration `migrations/facility` (`habitat`, `zone`, `zone_alert`, `incident` with a partial unique index of one open automatic ticket per zone, and `incident_update`).
- **Startup:** the first time the process needs Facility (an event, a query or a mutation), it syncs the floor plan and rebuilds the projection of active alerts and each zone's color from Monitoring's `ActiveAlertsQuery`.
- **GraphQL** (own fragment, `interfaces/graphql/facility.py`, composed with `merge_types`; the shared types moved to `common.py`): `ship`, `incidents` (cursor and filters by status and zone), `incident` (with its type and its history), `incidentTypes(category)`, `reportIncident`, `acknowledgeIncident` and `resolveIncident`, with typed errors (`NOT_FOUND`, `ALREADY_RESOLVED`, `ACTIVE_ALERTS`, `UNKNOWN_ZONE`, `UNKNOWN_TYPE`, `INVALID_SEVERITY`).
- **WebSocket:** new `habitat` topic with `incident.opened`, `incident.updated`, `incident.resolved` and `zone.status`, all with `seq` for resuming.
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 165 files, 4 architecture contracts kept, **662 tests** (19 skipped, Dev B's) and 96.84 % coverage. The end-to-end test also checks that a client that subscribes late recovers with `resume` the ticket and the laboratory's color, in order and without duplicates. Alert latency: 63 ms.
- **Acceptance criteria for F4,** all with a test: an alert opens exactly one ticket and paints the zone; a second alert does not open another; an automatic ticket with out-of-range values is not resolved; changing the floor plan changes the zones of `ship`; on restart the zone state is rebuilt.
- **TDD:** the domain, the WebSocket message tests and the exporter's started in RED. **The application service, the SQL repository and the GraphQL were written before their integration tests.** To check that those tests detect errors a mutation was made: with the close block disabled, the test fails.
- **Finding in the data:** the catalog validation found future rules shared between types (`power-bus` in two, `sensor-health` in three). They were separated (`power-bus-fault`, `power-bus-low`, `sensor-health-down`, `-calibration` and `-dosimeter`).
- **Differences from the plan:** there is no `incident_type` table (the catalog is loaded in memory, like the floor plan); there is one new table, `zone_alert`; `typicalZones` returns zone codes (`*` = any), while Dev B's mock uses names; there are no DataLoaders.
- **Risk:** with Facility connected, the slowest tick in the end-to-end test went up from 0.27 to 0.64 s (includes the initial rebuild). It stays under 1 s.

### B-020 · Remote review (November 15, 02:30)
- **What:** `git fetch --all --prune` and comparison of branches, without changing anything in the repository.
- **`dev-A`:** 21 commits ahead of `origin/dev-A` and none pushed. It includes the merges B-015 and B-016, F5, 5.4 and F4.
- **`testing`:** unchanged since PR #4 (`880c416`), which is already merged into `dev-A`.
- **`dev-B`:** 14 new commits that are not yet in `testing`:
  - interface for F10 (tasks of the day) and F11 (Ground panel), against mocks (`web/src/data/mocks/tasks.ts`);
  - F14 (voice with Whisper in Docker);
  - assistant with n8n and Ollama (phases 1 to 6), plus `src/spaceapp/devtools/`.
- **Dev B did not touch Dev A's folders.** Outside their area only `.gitignore` and a mypy exception for `faster_whisper` in `pyproject.toml` changed. `n8n/credentials/ollama.json` only carries a URL, no secrets.
- **Trial merge** (`git merge-tree dev-A origin/dev-B`): no conflicts.
- **PRs** (public GitHub API; `gh` is not installed): #1 closed, and #2, #3 and #4 merged. There are no open PRs.
- **Pending from what was proposed to the user:** push `dev-A`, open the PR to `testing`, review the real CI and do F9. New: the backend of F10 and F11 (Dev A's) is what the interface that Dev B already made is waiting for.
- **Decision that Dev B recorded** (logbook E18): n8n is mandatory for the assistant. That answers open question 2 of section 2.3; the user still has to confirm it.

### B-021 · Push of `dev-A` to GitHub
- **What (user's request):** `git push origin dev-A` (`9fb8bfe..1db03f4`). The 22 commits went up: the merges B-015 and B-016 (with the Dev B commits they bring), F5 (`9bed3c0`), 5.4 (`81686a1`), F4 (`286024c`) and the logbook B-020 (`1db03f4`). This record was pushed afterwards.
- **Verification:** `git rev-list --left-right --count dev-A...origin/dev-A` → `0 0`.
- **Pending:** open the PR `dev-A → testing` (`gh` is not installed: it is created from the web), have Dev B open theirs `dev-B → testing` and review the GitHub CI.

### B-022 · F10 and F11: tasks of the day and plan from Ground (backend)
- **User's request:** leave F9 for when the interface is ready and meanwhile do the backend of F10 and F11.
- **Aligned with Dev B's interface** (`origin/dev-B`: `features/tasks/model.ts` and `features/ground/model.ts`): same types, origins, states, `blockedReason`, `effective` and `sourceAlertId`, and the plan stages QUEUED → IN_TRANSIT → RECEIVED → APPLIED → CONFIRMED.
- **F10, `engagement` module:**
  - **Tasks of the day:** each active template gives one task per day, with no duplicates. Seven demonstration system templates in `data/engagement/templates.json`: three health routines and four ship tasks, taken from the artifact.
  - **Own tasks:** the crew creates, edits and deletes their own (HEALTH or SHIP). Those from Ground and from the system return `NOT_EDITABLE` or `NOT_DELETABLE`. Any task can be completed (with `effective`), snoozed or blocked with a reason; blocking does not delete it.
  - **Handlers:** an opened ticket creates an INCIDENT task and its resolution completes it. Each action of a recommendation is a measure of the day with `sourceAlertId`, which does not count toward the streak. Everything is idempotent (partial unique indexes).
  - **Streak:** only completed health routines count; neither Ground, nor incidents, nor alerts add to it.
  - **Applying a Ground plan** (one transaction): NEW, UPDATE and CANCEL on templates of GROUND origin. An invalid item is rejected alone, with a reason. Ground does not touch local templates, and a repeated or lower version is ignored. What was completed or created on board is kept and the cancellation applies to the future. It publishes `ground_plan_applied` with what was applied and what was rejected.
- **F11, `groundlink` module:**
  - **Ship (R9, `POST /api/v1/groundlink/inbound/plans`):** validates integrity (SHA-256 of the canonical JSON of version and items) and the shape of each item. A corrupt plan is rejected entirely with 422 and can be resent corrected with the same batch. A repeated or lower version answers 200 `ignored`; a new one, 202, and publishes `ground_plan_received`. When Missions applies the plan, it is marked and confirmed (`batch_acknowledged`).
  - **Ground (demo):** a draft, publication with the next version, only one publication in progress, and a simulated link with delay and cut (R5 `PUT /api/v1/groundlink/link` and `setGroundLink`). With the link cut the plan stays QUEUED and goes out when it comes back; if it is cut in flight, it goes back to the queue; the confirmation also waits for the link.
- **GraphQL** (fragment `interfaces/graphql/missions.py`): `tasks(day, kind, status)`, `streak`, `groundPlan`, `createTask`, `updateTask`, `deleteTask`, `completeTask`, `blockTask`, `snoozeTask`, `groundControl`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` and `setGroundLink`, with typed errors.
- **WebSocket:** new `crew` topic with `task.assigned`, `task.created`, `task.completed`, `task.blocked`, `groundplan.received`, `groundplan.applied`, `groundplan.confirmed` and `groundlink.state`.
- **Migrations:** `migrations/engagement` and `migrations/groundlink`. Contracts regenerated.
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 182 files, 4 architecture contracts kept, **707 tests** (19 skipped, Dev B's) and 95.89 % coverage. There is an HTTP test on the real app (relay on and link with 0.1 s delay): Ground publishes, the ship applies, Ground sees CONFIRMED and the crew sees the task.
- **Acceptance criteria for F10 and F11,** all with a test: own task without a link; incident task completed when the ticket is resolved; editing or deleting a Ground task gives a typed error; `effective` comes out in `task_completed`; a plan queued with the link cut that arrives, is applied and is confirmed when it comes back; the same plan twice leaves the tasks once; what was completed or created on board is not lost. Also the eight conflict rules in section 13.11.
- **TDD:** the `engagement` and `groundlink` domains and the WebSocket messages started in RED. **The services, the repositories and the GraphQL were written before their integration tests.** A control mutation was made: without the repeated-version check, the idempotency test fails.
- **Error fixed along the way:** when rejecting a corrupt plan its batch was saved, and that blocked the corrected resend with the same `batch_id`. The R9 test detected it and it was fixed with an `ON CONFLICT ... WHERE status = 'REJECTED'`.
- **Differences from the plan:**
  - no reminders or achievements tables;
  - `snoozeTask` instead of `snoozeReminder`;
  - the Ground panel does not filter by consent (the Crew module does not exist yet) nor authenticate the `ground` role;
  - Ground shares a database with the ship in the demo;
  - all tasks belong to the demonstration crew member.
- **For Dev B:** replace the task and Ground panel mocks with these operations and with the `crew` topic. The `groundControl` view follows the shape of their `GroundState` (`appliedVersion`, `templates`, `draft`, `published.stage` and `link`).

### B-023 · Push of F10 and F11, and PR to `testing`
- **What (user's request):** `git push origin dev-A` (`3183793..d083d7a`), with F10 and F11. This record was pushed afterwards.
- **PR `dev-A → testing`:** it could not be opened from here. `gh` is not installed, the Claude in Chrome extension was not connected and the built-in browser has no GitHub session. The user was given the link and the description in English to open it from the web.
- **Verification:** local `dev-A` and `origin/dev-A` equal (`0 0`). There were no open PRs.

### B-024 · Remote review (November 15, 06:00)
- **PR #5 `dev-A → main`:** merged by the user at 03:04 (local time) with `dev-A` at `3183793`. F4, F5 and 5.4 went into **`main`**, not `testing`. **F10 and F11 did not go in** (`d083d7a`) nor the logbook B-023 (`0611573`).
- **`testing`:** still at PR #4. It does not have Dev A's F4 or F5 or Dev B's new work.
- **`dev-B`:** one new commit (`f6d32b9`): the interface's assistant goes through the backend, n8n and Ollama. Their work since PR #4 (interface F10 and F11, F14, the assistant) **is not in `main` or `testing`**.
- **Interface:** only the assistant calls a real backend (`VITE_ASSISTANT_URL`). Dashboard, ship, incidents, tasks and Ground panel are still on mocks; the only GraphQL document is `dashboard.graphql`.
- **Trial merge `dev-A` + `dev-B`:** no conflicts.
- **CI:** `dev-B` and `testing` green; `dev-A` (`0611573`) in progress at the time of review.

### B-025 · Branch flow decision: integrate in `testing` and then `main` to dockerize
- **User's decision:** integration tests are done in `testing`, so as not to break the project. When it works there, it goes to `main` and then it is dockerized (F9).
- **Effect on the plan:**
  - **F9 comes after** `testing` works and is moved to `main`. It is not brought forward.
  - PRs go to **`testing`**: `dev-A → testing` (F4, F5, F10 and F11) and `dev-B → testing`. PR #5 `dev-A → main` had already been merged with F4 and F5, so `main` is ahead of `testing`; when `dev-A` reaches `testing` they are up to date.
  - Integration with the front end, the assistant and n8n is done **inside `testing`**, with both backends already together.
- **`dev-A` CI:** `0611573` green.
- **Pending items that come out of the `dev-B` review and are resolved when integrating in `testing`:**
  1. **The assistant is not in `main.py`.** Dev B tested it with his own development server (`devtools/assistant_server.py`, port 8000, "not the delivery server"). The composition root is Dev A's, so **connecting the assistant module, n8n and Ollama to `main.py` is Dev A's integration work**, and it depends on their code being in `testing`.
  2. **Port 8000:** the n8n workflow calls `host.docker.internal:8000` (`backend_url`) for its RAG and alert tools. Dev A's app must listen on 8000 and expose `/api/v1/assistant/tools/...`, or `backend_url` is changed in a single place.
  3. **Interface without proxy or CORS:** `web/vite.config.ts` only has a proxy for `/dev`, and the backend has no CORS. To consume `/graphql`, `/api` and `/ws` a proxy is needed (with `ws: true` for `/ws`) or CORS.
- **No code changes in this block.**

### B-026 · Attempt to open and merge the PRs to `testing`
- **User's request:** open and merge the PRs `dev-A → testing` and `dev-B → testing`.
- **It could not be done.** What was tried: `gh` is not installed; the Claude in Chrome extension was not connected; the built-in browser opens GitHub's comparison pages, but **with no session started** ("Sign in" appears and there is no button to create the PR). Signing in is something the user must do: the assistant does not type passwords or tokens, nor take one from git's credential store.
- **State of the PRs:** none open. `dev-A → testing`: 9 commits and 110 files, with no apparent conflicts. `dev-B → testing`: GitHub showed "Checking mergeability" at the time of review; the local trial merge with `dev-A` came out without conflicts.
- **Recommended order when merging:** first `dev-A`, then `dev-B`, and check `testing`'s CI between one and the other.
- **Pending:** the user opens and merges the PRs from the web, or signs in to the built-in browser or connects the Chrome extension so the assistant does it.

### B-027 · Dev A's logbook moves to `bitacora-dev-a.md`
- **User's request:** keep it under another name so there is no conflict when merging.
- **What:** `docs/bitacora.md` was moved with `git mv` to **`bitacora-dev-a.md`** at the root (renamed `logbook-dev-a.md` in the English translation), like Dev B's (`bitacora-dev-b.md`, now `logbook-dev-b.md`). Each developer writes only in their own. The references in `docs/tasks-dev-a.md` and `tools/docgen/README.md` were updated.
- **Effect on the PRs:** `testing` had the old file (from the earlier PRs) and nobody else changed it. The PR deletes it without conflict, and the new file does not exist in any other branch. `dev-B` does not touch `docs/bitacora.md`, so the merge stays clean.
- **The PRs and this logbook:** the change is on `dev-A`. If the PR `dev-A → testing` is already open, these commits must be pushed first.
- **Backup copy:** `~/Documentos/space_apps/bitacora-dev-a.md` (formerly `space_apps/docs/bitacora.md`).

### B-028 · Front-end specification
- **User's request:** an `.md` with the project's specifications for the front end, indicating each section and what data is consumed and shown.
- **File:** `docs/front-spec.md` (new; originally written in Spanish for Dev B as `docs/especificacion-front.md`).
- **Contents:** common rules of the interface; how it connects (GraphQL, `/ws`, REST and proxy); map of the five screens (Cabin, Facility, Tasks, Assistant and Ground panel) with, for each one, the datum it shows, the query or `/ws` message it comes from, the actions and their typed errors; catalog of the `/ws` messages; which mock each operation replaces; differences in names and types with the current front end; backend gaps; connection order and how to bring up the backend.
- **Method:** it was cross-checked against the generated contracts (`contracts/schema.generated.graphql` and `openapi.json`) and against the front-end code in `origin/dev-B` (`App.tsx`, `Root.tsx`, `DemoPanel.tsx`, `features/*`, mocks).
- **Corrected while writing:** a first version said that demo mode is hidden in `jury`; the `DemoPanel` shows it there too, and it was fixed. It was also verified that stopping an inactive scenario gives no error.
- **Mismatches found between the front end and the backend (documented in section 7):**
  - different scenario keys (`co2-alto` versus `co2_slow`, `fuga-presion` versus `pressure_leak`, etc.);
  - the front end sends the mock's zone id and the backend expects its code;
  - the front end's `RECIBIDA` template status does not exist in the backend, and the backend's `REJECTED` stage is not in the front end;
  - the front end shows a ticket code (`t.code`) that the backend does not return;
  - `Rule` in GraphQL carries no thresholds: they come from `/api/v1/rules/catalog.json`.
- **No code changes.**

### B-029 · Readable ticket code and thresholds in `Rule`
- **User's request:** apply the recommendation on the mismatches with the front end (points 4 and 5) and redo the specification.
- **Point 4, ticket code (`INC-0001`):**
  - migration `migrations/facility/versions/0002_incident_number.py`: `number` column with identity and a unique constraint. It is a new migration because 0001 is already in `main`;
  - `incident_code(number)` in the domain (four digits minimum);
  - `insert_ticket` returns the number and the service puts it in the `IncidentOpened.code` event, which is optional so as not to invalidate old events;
  - GraphQL: `Incident.code`; `/ws`: `incident.opened` carries `code`, so a new ticket is drawn in full without requesting the list.
- **Point 5, thresholds:** `Rule` in GraphQL adds `kind`, `operator`, `threshold`, `unit` and `windowS`, so the charts draw their limits without calling REST.
- **Contracts regenerated** (`schema.generated.graphql` and `ws-messages.schema.json`). **Additive** change: no existing field changed or was removed, so it does not break Dev B's front end.
- **Specification:** `docs/front-spec.md` moved to version 2. The header, section 2 (it no longer depends on `catalog.json`), the charts and limits of 4.2 (with how to draw them), the ticket list, the `/ws` catalog, section 7 and section 9 (the two resolved gaps are removed) change. Points 1 to 3 (scenario keys, zone id versus code and `RECIBIDA`/`REJECTED` states) belong to the front end and remain described in section 7.
- **Verification** (`scripts/check.sh`): ruff with no errors, strict mypy with no errors in 182 files, 4 architecture contracts kept, **711 tests** (19 skipped, Dev B's) and 95.90 % coverage.
- **New tests:** `incident_code`; sequential codes in opening order, in GraphQL and in the event; thresholds of `env-co2-1h` and a trend rule; `code` in the `/ws` message; and the migration against a database with three prior tickets (all receive a different number).
- **TDD:** the tests were written first and failed (RED: `incident_code` did not exist). The service and migration tests were written after the code and verified green.
- **For Dev B:** the ticket code has four digits (`INC-0001`); if their tests expect `INC-001`, they must be adjusted.

### B-030 · Push of `dev-A` (logbook, remote review, specification and B-029)
- **What (user's request):** `git push origin dev-A` (`0611573..6b56088`), to the `dev-A` branch and no other. 5 commits went up: B-024 and B-025 (branch flow), B-026 (attempt to open the PRs), B-027 (the logbook moves to `bitacora-dev-a.md`), B-028 (front-end specification) and B-029 (ticket code and thresholds in `Rule`). This record was pushed afterwards.
- **Verification:** `git rev-list --left-right --count dev-A...origin/dev-A` → `0 0`.
- **Effect:** `dev-A` now carries the final contract and specification v2 for Dev B. `testing` and `main` do not change: no PR was opened.
- **Pending:** open and merge the PRs `dev-A → testing` and `dev-B → testing` (the user, from the web).

### B-031 · Second attempt to open and merge the PRs to `testing`
- **User's request:** reconnect Git and open and merge the PRs `dev-A → testing` and `dev-B → testing` with descriptions in English.
- **Git:** connected. `git ls-remote`, `fetch` and `push` work. What fails is the GitHub part (creating and merging PRs).
- **Paths tried:** the Claude in Chrome extension still does not connect; the built-in browser **refused navigation to github.com**; `gh` is not installed; the session has no GitHub connector and the connector registry does not offer one. No token from git's credential store was used.
- **State:** no PR open. `testing` contains neither `dev-A` nor `dev-B`.
- **`dev-B` moved** to `38a41ae` (RAG with hybrid search and vectors, and front-end test adjustments). The trial merge `dev-A` + `dev-B` and `testing` + `dev-A` is still **without conflicts**.
- **Delivered:** `pr-dev-A-to-testing.md` and `pr-dev-B-to-testing.md` (title, link and description in English), sent to the user.
- **Option pending authorization:** merge `dev-A` and then `dev-B` into `testing` from Git, verifying the merged tree with `scripts/check.sh` before pushing. It skips the PRs, and is not done without the user's express authorization.

### B-032 · Direct merge of `dev-A` and `dev-B` into `testing`
- **User's request:** "merge" ("fusiona"), after not being able to open the PRs from here (B-031). The direct merge through Git was chosen, without PRs.
- **What:** local branch `testing` from `origin/testing` (`880c416`); `git merge --no-ff origin/dev-A` (`ad30a1f`) and then `git merge --no-ff origin/dev-B` (`38a41ae`). **No conflicts.** Result `67778b7`.
- **Interruption:** the session was cut during the first verification; nothing had been pushed. On resuming, the integration tests failed because **Docker was off** (not because of the code): `docker-desktop` was started again (see section 5).
- **Verification on the merged tree, before pushing** (`scripts/check.sh`): `uv lock --check` correct, ruff with no errors, strict mypy with no errors in 199 files, 4 architecture contracts kept, **930 tests** (21 skipped) and 95.44 % coverage.
- **Push:** `git push origin testing` (`880c416..67778b7`), fast-forward. `origin/testing` now contains `dev-A` and `dev-B`.
- **No PRs:** no descriptions remain on GitHub; those in `pr-dev-A-to-testing.md` and `pr-dev-B-to-testing.md` remain as a record. `testing`'s CI is the second verification.
- **Next:** integration inside `testing` (Dev B's assistant in `main.py`, port 8000 and front-end proxy) and connecting the front end to the real API. When it works, move to `main` and dockerize (F9).

### B-033 · Whole project translated to English
- **User's request:** everything in the project (code, documentation, logbooks, comments) must be in English; only the chat with the user stays in Spanish. Scope: the `dev-A` branch only. The user also decided to translate the contract enums and the RAG data.
- **Branch:** `a/english-translation`, cut from `origin/dev-A` (`9c37a59`). Nothing is committed yet (git has no identity configured on this machine).
- **Contract values renamed** (code, migrations, rule and facility catalogs, knowledge data, web, regenerated contracts): `ATENCION/ALERTA/CRITICO` → `ATTENTION/ALERT/CRITICAL`, `VERIFICADO/NO_VERIFICADO` → `VERIFIED/UNVERIFIED`, `ABIERTA/RECONOCIDA/RESUELTA` → `OPEN/ACKNOWLEDGED/RESOLVED`, `SALUD/NAVE/INCIDENTE` → `HEALTH/SHIP/INCIDENT`, `TIERRA/SISTEMA/TRIPULACION` → `GROUND/SYSTEM/CREW`, plan stages (`DRAFT/QUEUED/IN_TRANSIT/RECEIVED/APPLIED/CONFIRMED/REJECTED`), recurrences `DIARIA/UNA_VEZ` → `DAILY/ONCE`, `cause_hint` → `ENVIRONMENT/BODY/UNDETERMINED`, profile `jurado` → `jury`, habitat `nave-transito` → `transit-ship`, sensor domains `cuerpo/cabina/radiacion` → `body/cabin/radiation`, plus the rule kinds, zone kinds, hazard key and action keys. `TB` (Technical Brief) and `DEMO` are unchanged. **Databases created with the old migrations must be recreated.**
- **Files renamed:** `bitacora-dev-a.md` → `logbook-dev-a.md`, `bitacora-dev-b.md` → `logbook-dev-b.md`, `docs/plan-arquitectura.md` → `docs/architecture-plan.md`, `docs/tareas-dev-a.md` → `docs/tasks-dev-a.md`, `docs/tareas-dev-b.md` → `docs/tasks-dev-b.md`, `docs/especificacion-front.md` → `docs/front-spec.md`, and the challenge notes → `docs/spaceapps-challenge-notes.md`.
- **RAG behaviour change:** the Spanish–English glossary and every Spanish-specific query feature were removed (`domain/glossary.py` became `domain/terms.py`; `glossary_es_en.json` and `eval_questions_en.json` were deleted and the evaluation sets are now English). The old metrics (9 of 16 and 1 of 9 in Spanish) no longer apply and could not be re-measured: no PDFs are in the repository. The index must be rebuilt with `--rebuild` and the evaluation run again.
- **Verification:** ruff and ruff format clean, strict mypy with no errors (182 files), import-linter 4 contracts kept, 544 unit tests (19 skipped), 165 integration tests against PostgreSQL, 123 web tests, lint and typecheck of the web app. Run with `PYTHONUTF8=1` on Windows.
- **Open:** `tests/unit/test_resilience.py::test_the_relay_survives_an_unreachable_database_and_still_stops` fails on Windows only (timeout, unrelated to the translation). Dev B's work on `testing` and `dev-B` is not translated and will conflict on every file touched here.

---

## 4. Project files by area

| Area | Location | Created by |
| --- | --- | --- |
| Context documents | `docs/spaceapps-health-monitor-context.md`, `docs/spaceapps-challenge-notes.md` (originally `docs/spaceApps 4186…md`) | User |
| Architecture plan | `docs/architecture-plan.md` | Assistant (generated) |
| Dev B's tasks | `docs/tasks-dev-b.md` | Assistant |
| TDD report F0 and F1 | `docs/tdd/f0-f1.tdd.md` | Assistant |
| Front-end specification | `docs/front-spec.md` | Assistant |
| Logbook | `logbook-dev-a.md` | Assistant |
| Dev A's tasks | `docs/tasks-dev-a.md` | Assistant |
| Plan and artifact generator | `tools/docgen/` | Assistant (moved from the *scratchpad*) |
| Dev A's backend (Blocks 1 and 2) | `src/`, `tests/`, `migrations/`, `docker/`, `scripts/`, `rules/`, `data/` | Assistant |
| Composed GraphQL (F5) | `src/spaceapp/interfaces/graphql/` | Assistant |
| Ship and incidents (F4) | `src/spaceapp/modules/facility/`, `migrations/facility/`, `data/facility/` | Assistant |
| Tasks and plan from Ground (F10, F11) | `src/spaceapp/modules/engagement/`, `src/spaceapp/modules/groundlink/`, `migrations/{engagement,groundlink}/`, `data/engagement/` | Assistant |
| Generated contracts for Dev B | `contracts/schema.generated.graphql`, `contracts/openapi.json`, `contracts/ws-messages.schema.json` | Assistant (generated) |
| TDD evidence reports | `docs/tdd/f0-f1.tdd.md`, `docs/tdd/f2-f3.tdd.md` | Assistant |

---

## 5. Changes outside the repository

Everything that was done on the user's machine, so it can be reverted.

| Change | Detail | How to revert |
| --- | --- | --- |
| `docker-desktop` service started | User service started with `systemctl --user start` (again on November 15, B-032). It was **not enabled** at startup | `systemctl --user stop docker-desktop` |
| `uv` 0.13.8 installed | In `~/.local/bin/uv`. Downloaded from the official `astral-sh/uv` *releases* with SHA-256 verified | Delete `~/.local/bin/uv` |
| Python 3.12.16 downloaded | By `uv`, in `~/.local/share/uv/python/` | `uv python uninstall 3.12` |
| Image `pgvector/pgvector:pg16` downloaded | For the integration tests and the compose | `docker rmi pgvector/pgvector:pg16` |
| Project virtual environment | `.venv/` inside the repository | Delete `.venv/` |
| Container `spaceapp-postgres-1` and its volume | Created for the real test and **removed** when finished | Already reverted |
| testcontainers containers | Ephemeral, removed when the tests finished | Already reverted |
| Local preview servers | Ports 8765 to 8768 and 8010, stopped | Already reverted |
| Block 2 live test | Container `spaceapp-postgres-1` and its volume, and the application on port 8011. Stopped and removed when finished | Already reverted |
| Cloned repository | `~/Documentos/SpaceOverflow` (clone of `Julio-Cuellar/SpaceOverflow`, branch `dev-A` with Dev A's work, already pushed to GitHub) | Delete the folder `~/Documentos/SpaceOverflow` |
| Local merges on `dev-A` | B-015 (`dev-B`) and B-016 (`origin/testing`), **not pushed** | `git reset --hard origin/dev-A` (discards the two merges and the uncommitted work) |
| `git stash` in the clone | "wip F5 realtime+graphql antes de fusionar testing" (wip F5 realtime+graphql before merging testing). It was already reapplied: it can be deleted | `git stash drop` |
| Backup of the F5 work | `wip-f5.diff` and `wip-f5-untracked.tgz` in the session's temporary *scratchpad* | Deleted with the session |
| `strawberry-graphql` 0.341.2 | In the clone's `.venv`, through `uv sync` | `uv sync` without the dependency |

**Not touched:** the containers of another of the user's projects (`clinerya-postgres`, `clinerya-backend`, `clinerya-frontend`, `clinerya-rabbitmq`).

**Observation:** the artifact is listed as "Anyone with the link". That setting was not changed by the assistant.

---

## 6. Errors and fixes

| # | What happened | How it was fixed |
| --- | --- | --- |
| E-1 | I said the P0 cut was 41 h. It is 40 h | Fixed in the next message and in the plan (computed from the data) |
| E-2 | I called `uplink` the module that sends data to Ground, and in space operations that is the *downlink* | Renamed to `groundlink` in the document, the artifact and the code |
| E-3 | A first version of the TDD report had 4 wrong per-file test counts | They were checked against `pytest --collect-only` and fixed |
| E-4 | A test of mine wrote in the wrong field of the Ground form | It was an error of the test *script*, not of the product. It was repeated with the right field |
| E-5 | Twice, `pkill -f` stopped my own shell (code 144) because the pattern matched the command itself | An `awk` filter that excludes the process itself was used. It left nothing half done |
| E-6 | `import-linter` failed because of `ignore_imports` patterns without matches | `unmatched_ignore_imports_alerting = "none"` |
| E-7 | Strict mypy gave 16 errors | Fixed without relaxing strict mode (see the TDD report) |
| E-8 | Port 5432 was occupied by another project | This project's database uses 5433 |
| E-9 | `make` is not installed | `scripts/check.sh` was added |
| E-10 | In the built-in browser, some screenshots came out blank and text with accents came out broken | It is an effect of the preview server (no `charset`) and of the capture. It does not affect what was published |
| E-11 | The generator's third test only checked that `stderr` was empty, so it proved nothing useful | It was replaced by a test that requires an unknown marker to make the generation fail and be named |
| E-12 | In `tasks-dev-a.md` the F2 subtasks added up to 4.25 h and the phase is 4 h | Subtask 2.2 was reduced to 0.75 h and the sums of all phases were verified |
| E-13 | One of my handler expectations was wrong: with the test's scaled window, a PIO₂ of 121 mmHg meets the absolute limit (122) | The test was fixed, not the engine |
| E-14 | The trend detector required 20 baseline points, but the atmosphere is sampled every 5 s: it would never have fired. The simulator's design showed it | Test first (RED), and per-rule window parameters in the catalog |
| E-15 | The pressure rate-of-change rule used a 60 s window: a real leak averages about 6 psi/min and did not reach 13.5 | Test first and a 10 s window |
| E-16 | My leak test case evaluated second 30, where the change in 10 s is 0.97 psi and the rule exempts it by correct design | The case was fixed and a test that documents the exemption was added |
| E-17 | 19 integration tests failed at once: a text replacement in `conftest.py` was not applied because `ruff format` had already reformatted the list | It was edited against the real text |
| E-18 | Another text replacement (in the engine) was not applied either for the same reason, without warning | It was detected with `grep` and applied. Lesson: check every bulk replacement |
| E-19 | A GraphQL test from the earlier session expected there to be no resolved alerts after the CO₂ scenario. The pre-alert is resolved when it is replaced by the alert (`supersedes`) | The test was fixed, not the code: it now requires the resolved ones to be from other rules |
| E-20 | Another test expected 20 raw pressure samples in 30 s, but the test advances the simulation in steps of 5 s (7 samples) | The test was fixed: it requires one sample per tick |
| E-21 | The first end-to-end latency measurement (1.9 s) was wrong: it read the socket after all the ticks and packed 330 simulated seconds into 5 s of clock, so the alert waited behind later readings | The test reads in parallel and advances at real pace (one tick when the relay finished the previous one). Measured: 47 to 73 ms |
| E-22 | The F5 work from an earlier session was left with no commit and no logbook entry | It was recorded in B-017. Lesson: close each session with the logbook entry even if the block is not finished |

---

## 7. Maintenance risks

1. ~~The plan and artifact generators lived in a temporary folder.~~ **Resolved in B-011.** The source is in `tools/docgen/` and a test fails if `docs/architecture-plan.md` stops matching it.
2. ~~A dedicated document for Dev A was missing.~~ **Resolved in B-012:** `docs/tasks-dev-a.md`.
3. **The published artifact is updated by hand.** The generator creates `tools/docgen/out/plan.html`, but publishing it over the same link is a manual step. If the data changes, the artifact stays out of date until it is republished.
4. **The plan still lacks formal confirmation.** The execution relies on the user's "execute" for Block 1.
5. **No commits.** Until the first one is made, the history lives only in this logbook and in the TDD reports.
6. **Three sections of the plan depend on open decisions** (RAG, n8n and F12). Dev B can move forward with the assumptions in section 2.2.
7. **The `crew` hours have no assigned phase** (baseline and consents). In F2 nothing from `crew` was needed. It is left for F15 and for when there are baseline-relative rules.
8. ~~A severity escalation event is missing.~~ **Resolved in Block 2:** each rule has a fixed severity and raising the level is resolve and raise. It remains to be agreed with Dev B whether the gateway maps `alert.updated` to the acknowledgement.
9. **Monitoring performance with real windows.** With a 1 h window it queries about 3,600 readings per metric and zone on each batch. It was not measured. `rollup_mean` already exists as an alternative.
10. **Milestone I2 depends on the gateway (F5).** B continues with his recordings until I5.
11. **The published artifact is out of date** relative to the regenerated data model (rules, alerts and scenarios have new columns). It remains to be republished.

---

## 8. How to check the current state

```bash
cd /home/julio_jcode/Documentos/space_apps
scripts/check.sh                                              # ruff, mypy, import-linter and pytest with coverage
docker compose -f docker/compose.yaml up -d --wait postgres   # local database on port 5433
uv run python -m spaceapp.platform.migrate platform           # migrations
uv run uvicorn --factory spaceapp.main:create_app             # API: /health and /ready
uv run python tools/docgen/build.py --artifact-url <URL>      # regenerates the plan and the interactive page
```

The integration tests need Docker running (`systemctl --user start docker-desktop`).

---

## 9. Next steps

1. **F9 (delivery to the jury):** Dockerfile, full compose with `jury` profile and migrations of all modules at startup. Then F10 (tasks) and F11 (plan from Ground).
2. **Push `dev-A`** (two local merges and F5) when the user asks, directly or through a PR to `testing`.
3. **Contract review by Dev B (I0):** each module's `contracts.py`, `event_registry.py` and the in-memory bus.
4. **Republish the artifact** to reflect the current data model (user's decision).
5. **Pending decisions** from section 2.3.
6. **Notify Dev B** of the generated contracts, that `schema.graphql` is still his draft, of the new `habitat` topic and that `typicalZones` carries zone codes.
