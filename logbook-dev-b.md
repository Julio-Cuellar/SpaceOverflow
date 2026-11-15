# Dev B's logbook · health monitor for astronauts

> Record of what is done, how and with what evidence. Reference plan: `/home/juls_d3v/Descargas/tasks-dev-b.md` (with `architecture-plan.md` and `spaceapps-health-monitor-context.md`).
> Entries in chronological order. They are never deleted: if something changes, a new entry that corrects it is added.

## How we work (method)

- **TDD per task:** RED (test written and run, fails for the expected reason) → GREEN (minimal implementation, the same test passes) → REFACTOR (without changing behavior, tests green) → coverage.
- **Evidence:** each cycle records the exact command and an excerpt of the output. What was not run is marked as unverified.
- **Git:** since E08 the project is a repository (`origin`: `Julio-Cuellar/SpaceOverflow`) and Dev B's work lives on the `dev-B` branch. Until E07 there were no commits; the evidence of those cuts is in this logbook. From E08 on, one commit is made per phase or cut.
- **States:** `DONE` (verified with evidence), `PARTIAL` (something was left out, with a reason), `PENDING`, `BLOCKED` (depends on Dev A or on a decision).
- **The project's honesty rule:** every datum without a verified source is marked `DEMO`. The language model never decides an alert.

## Phase map and status

| Phase | Topic | Status | Note |
| --- | --- | --- | --- |
| F0 | Foundations (web, codegen, mocks) | PARTIAL | Done: web, tests, codegen, mocks, contract draft, CODEOWNERS and CI (the CI has not yet run on GitHub). Freezing the contract with Dev A (I0) is missing |
| F8 | Knowledge with demo data | PARTIAL | Domain, idempotent use case, DEMO catalog, facades and passage search tested (29 tests). Persistence and A's outbox are missing |
| F6 | Cabin interface | PARTIAL | Status light, cards, human body, SVG charts with threshold and anomaly, waiting state, alert panel and WS queue, all wired in `App` with demonstration data. The `useWs` hook connected to `/ws` (I2) and the CO₂ trend in the cabin are missing |
| F7 | Ship panel | PARTIAL | Floor plan from `zone.layout`, ticket pins, ordering and "resolve" rule, per-zone charts with pause, report form, filterable catalog and demo mode by profile. The full catalog of 61 types and the backend are missing |
| F12 | RAG over NASA PDFs | PARTIAL | Manifest with licenses, fragmentation by requirement, PDF reading, idempotent ingestion, search with es→en glossary, fallback to demo and evaluation, tested with synthetic PDFs and then with the 7 real PDFs (2,087 fragments, E10). **Retrieval below the plan's threshold:** 56 % on the main set, 11 % on the held-out one, 0 answers without a source. The passage search in the web (12.6) and the embeddings model decision are missing |
| F13 | Text assistant and Ollama | PARTIAL | Backend: use case with an 8 s limit, null and Ollama adapters, `answer_ready` event (15 tests). Web: Assistant tab with demonstration data. GraphQL, SQL persistence, real Ollama tested and optional n8n are missing |
| F14 | Voice with Whisper | PENDING | |
| F9 | Delivery (Docker, no internet) | PENDING | joint with A |
| F10 | Tasks (interface) | PENDING | |
| F11 | Mission control panel | PENDING | |
| F16 | Alexa as a fallback | PENDING | only if Whisper gets stuck |

---

## Entries

### 2026-11-14 · E01 · Environment preparation

- **What:** the working directory was reviewed (it was empty). The structure `web/`, `contracts/`, `data/knowledge/`, `src/spaceapp/modules/knowledge/` and `tests/knowledge/` was created.
- **Tools detected:** Node 24.22.1, npm 11.19.1, Python 3.14.4. `uv` is not installed; Python's `venv` will be used. The npm and pip registries respond.
- **Web installed:** react 18, react-dom 18, urql, graphql, uplot (dependencies); vite, @vitejs/plugin-react, typescript, vitest 3, jsdom, @testing-library/react 16, jest-dom, user-event, msw, @graphql-codegen/cli and client-preset (development).
- **Deviation:** `esbuild` showed an npm 11 `install-scripts` warning. It will be reviewed at the first `vite build`.
- **Contracts:** the plan says the GraphQL schema and the WS messages are frozen at I0 together with Dev A. Dev A has not delivered anything yet. A **draft** will be written in `contracts/`, marked as pending review, so that B can generate types and mocks.
- **Status:** PARTIAL. Environment ready; configuration and tests are missing.

### 2026-11-14 · E02 · F0 interface foundations (TDD)

**RED → GREEN cycle, first pass**

- **RED:** 6 suites were written (severity, SevPill, EvidenceBadge, Banner, WS player, sample dashboard). Command: `npx vitest run`. Result: `Test Files 6 failed (6)`, cause `Failed to resolve import "./SevPill"` and similar. It failed because of a nonexistent module, which is the expected failure.
- **GREEN:** the minimum was implemented: `shared/lib/severity.ts`, `shared/lib/evidence.ts`, `shared/ui/{SevPill,EvidenceBadge,Banner}.tsx`, `data/ws/{types,replay}.ts`, `data/mocks/fixtures.ts`. Result: `Tests 19 passed (19)`.
- **Deviations fixed during GREEN:**
  1. `tsconfig.json` with `jsx: react-jsx` was missing. Without it, Vitest failed with `React is not defined`.
  2. Testing Library did not clean the DOM between tests, because Vitest does not expose globals. `cleanup()` was added in `src/test/setup.ts`.
  3. `@vitest/coverage-v8` was missing. It was installed.

**RED → GREEN cycle, second pass (contract, mock and entry point)**

- **RED:** `contract.test.ts` (`dashboard` document against the schema), `handlers.test.ts` (MSW answers `Dashboard`), `recordings.test.ts` (recording with `telemetry.tick`), `App.test.tsx` (banner on opening). Result: `4 failed`, 19 passed.
- **GREEN:** `contracts/schema.graphql` (draft), `web/src/data/graphql/documents/dashboard.graphql`, `data/mocks/handlers.ts`, `data/mocks/ws/recordings.ts`, `App.tsx`, `main.tsx`, `index.html`, `shared/tokens.css`, `codegen.ts`. Result: `Tests 26 passed (26)`.
- **Deviation:** `import.meta.url` is not a `file://` path in the jsdom environment. The contract test resolves the path from `process.cwd()` (always `web/`).

**Verification of F0 acceptance criteria**

| Criterion | Evidence |
| --- | --- |
| `npm run dev` opens with banner | `App.test.tsx` checks it in jsdom. Checking in a browser is missing (see pending items) |
| `npm run codegen` generates types | `npm run codegen` → `✔ Generate outputs` |
| Mock returns `dashboard` | `handlers.test.ts` passes with MSW |
| Player emits `telemetry.tick` | `recordings.test.ts` and `replay.test.ts` pass |
| Frozen schema (I0) | **No**: the draft is pending Dev A's review |

**Coverage and build:**

- `npx vitest run --coverage` → lines 91.89 %, functions 100 %, branches 81.25 %, statements 89.47 %. It exceeds the 80 % threshold.
- `npx tsc --noEmit` → no errors (exit 0).
- `npx vite build` → `✓ built in 154ms`, bundle 140.92 kB (gzip 45.83 kB).

**B's decisions (they do not come as is from the plan):**

1. **Four severity levels with their own symbol:** `● Normal`, `▲ Attention`, `◆ Alert`, `■ Critical`. The plan gives the symbol for Normal, Attention and Critical, but not for Alert. ◆ was chosen so that each level has a distinct shape.
2. **High CO₂ gives `ALERT`, which is shown in red:** the plan says "changes the status light to red". In the plan, red corresponds to Alert and magenta to Critical on the ship. That correspondence is kept.
3. **`SIMULATED` is an origin and a label, not a value of the contract's `EvidenceState`:** the contract's enum has `VERIFIED | TB | DEMO | UNVERIFIED`. The `EvidenceBadge` component does show `SIMULATED` when the origin is simulated.
4. **Versions:** Vitest 3 and Vite 8 brought two copies of Vite. It was moved to Vitest 5.1.0 with Vite 8.3.8, a single tree.

**Pending items of F0:**

- CODEOWNERS and B's CI job: they require a repository with a remote. They have not been created.
- Check startup in a browser (`npm run dev`) to see the banner visually.
- Contract: pending Dev A's review before freezing at I0.

**Status:** F0 PARTIAL (closes when there is a repository for CODEOWNERS and CI).

### 2026-11-14 · E03 · F8 knowledge with demonstration data (TDD, Python)

**Environment:** `.venv` at the root with Python 3.14, pydantic 2.14.3, pytest 9.2.0, ruff and mypy. `pyproject.toml` with `pythonpath = ["src"]`.

**RED:** `tests/knowledge/` with four files (recommendation per alert, contract, catalog and facade) plus `conftest.py`. Command: `.venv/bin/python -m pytest tests/knowledge -q`. Result: collection error `ModuleNotFoundError: spaceapp.modules.knowledge.adapters.outbound.demo_source`. It fails because of a nonexistent module, as expected.

**GREEN:** module `spaceapp.modules.knowledge` with `contracts.py` (payloads of `alert_raised` and `recommendation_ready`), `domain/model.py`, `ports/__init__.py`, `application/handle_alert_raised.py` (idempotent use case), `adapters/outbound/{demo_source,memory}.py`, `facade.py` and the catalog `data/knowledge/demo_catalog.json` with 8 rules and 16 actions. Result: `24 passed`.

**Guarantees tested (F8 criteria):**

| Plan criterion | Test |
| --- | --- |
| `env-co2-1h` gives a recommendation with at least 2 actions | `test_co2_alert_gets_at_least_two_actions` |
| Citation with document, requirement and evidence state | `test_co2_alert_gets_a_citation_with_document_requirement_and_evidence_state` (V2 6004, VERIFIED) |
| Every answer carries the DEMO label | `test_recommendation_is_labelled_as_demo_and_says_it_is_not_from_nasa` and `test_every_rule_is_labelled_as_demo_source` |
| Duplicate event does not duplicate | `test_same_event_delivered_twice_does_not_duplicate_the_recommendation` |
| One recommendation per catalog rule | `test_every_rule_in_the_catalog_gets_a_recommendation` (8 parametrized cases) |
| `RecommendationReady` contract per the plan | `test_recommendation_ready_has_exactly_the_payload_of_the_plan` |
| No language model or network | The use case receives no composer or HTTP client |

**Quality:**

- `ruff check src tests` → `All checks passed!` (the import order was fixed).
- `ruff format` → 1 file reformatted.
- `mypy` (strict mode, `src`) → `Success: no issues found in 14 source files`. A leftover `type: ignore` was removed.

**Decisions and deviations:**

1. **`source_kind` does not travel in the event.** The `recommendation_ready` payload is the plan's (section 4.1). Adding a field requires asking Dev A first. That is why the DEMO label goes in the recommendation body ("This recommendation uses demonstration data, not NASA data"). `source_kind` exists only in the internal model. **Pending:** request to Dev A to add `source_kind` to the event.
2. **Local inbox, not the platform's.** Idempotency uses an `Inbox` port with an in-memory adapter. At I1 the real outbox inbox (Dev A's) replaces it. Until then, idempotency holds only within the process.
3. **No transaction with outbox yet.** The plan asks to save the recommendation and publish the event in the same transaction. Without a database or outbox it cannot be tested. The use case is already ordered so that the substitution is direct.
4. **Deterministic id:** `uuid5(alert, rule)`. The same alert and the same rule always produce the same recommendation id, even if they arrive with a different `event_id`.
5. **Unknown rule:** it raises `UnknownRuleError` before marking the event. This way a relay retry can process it later. This follows the plan's rule that the relay retries and moves to `dead` after 8 attempts.
6. **Citations of demonstration rules:** `env-rh` and `env-t` cite the verified anchor V2 6013, but their range is DEMO, so their `evidence_state` is `DEMO`. `env-tendencia` has no standard requirement, and is cited as "Demonstration (no requirement)".

**Pending items of F8:**

- Alembic migration of the `knowledge` schema and real persistence in PostgreSQL (depends on A's platform).
- Integration with the real bus (I1, I4).

**Status:** F8 DONE in its domain and use case part, with tests. PARTIAL for what depends on A (persistence, outbox, bus).

### 2026-11-14 · E04 · F6 and F7 (first cut, TDD)

**RED → GREEN pass per component.** Command: `npx vitest run <folder>`. Each component was written with its test; the REDs observed were `Failed to resolve import` for a nonexistent module.

| Module | RED observed | GREEN |
| --- | --- | --- |
| `features/cabin/AlertPanel.tsx` | Yes (nonexistent module) | 7 tests |
| `features/cabin/CabinPanel.tsx` | Yes (nonexistent module) | 4 tests |
| `data/ws/stream.ts` | **Not observed.** Test and code were written in the same batch and passed the first time | 6 tests |
| `features/ship/ShipPlan.tsx` | Yes (nonexistent module) | 9 tests (with edge cases added) |
| `features/ship/model.ts` | Yes (nonexistent module) | 5 tests in `rules.test.ts` |

**Method note:** in `stream.ts` no RED was run before implementing. This breaches the cycle set at the start. The test is still valid as a specification, but there is no evidence that it failed before. For future pieces the RED will be run before writing the implementation.

**Quality of the full pass (end of E04):**

- `npx vitest run` → `Test Files 15 passed (15)`, `Tests 60 passed (60)`.
- `npx vitest run --coverage` → lines 100 %, functions 100 %, statements 100 %, branches 92.53 %. It exceeds the 80 % threshold in all four metrics.
- `npx tsc --noEmit` → exit 0.

**Changes that came up when reaching coverage:**

1. **`zoneStatus` was removed from `features/ship/model.ts`:** nobody used it, so it was dead code. It was preferred to remove it rather than test it.
2. **`src/main.tsx` was left out of coverage:** it only mounts the app and has no logic. The build and, later, the browser test verify it.
3. **Edge cases added:** empty player list, repeated `start()`, rule without a requirement in the alert panel, space key on the floor plan, resolved ticket not marked on the floor plan, and critical zone with a dashed stroke (the shape accompanies the color).

**B's decisions in this cut:**

- **Acknowledge:** `AlertPanel` only emits `onAcknowledge`. The GraphQL mutation `acknowledgeAlert` arrives when there is a backend (I2 or later).
- **`aria-live="assertive"` only for `CRITICAL`:** the plan asks for the critical alert to be announced with `aria-live`. The others stay at `off` so as not to interrupt.
- **The floor plan paints the state with text and shape:** each zone carries its symbol and its label (`Airlock, Alert`). Critical zones have a dashed stroke.
- **WS queue without React for now:** `createStream` is pure logic. The `useWs` hook will consume it in the next phase, when `/ws` is connected.

**What was NOT done in F6 and F7 (and why):**

- **uPlot charts and SVG human body (F6.4, F6.5):** they have no tests yet. They are left for the next cut.
- **`useWs` hook and connection to `/ws`:** depends on A delivering the gateway (I2). Until then, the queue is tested on its own.
- **Report form, incident catalog and demo mode (F7.5 to F7.7):** pending.
- **Per-zone charts (F7.3):** pending.

**Status:** F6 PARTIAL, F7 PARTIAL.

### Status summary at the close of the session

| Phase | Status | Tests |
| --- | --- | --- |
| F0 | PARTIAL (CODEOWNERS and CI are missing, they need a repository) | 26 web |
| F8 | DONE in domain and use case. PARTIAL for what depends on A | 24 Python |
| F6 | PARTIAL | included in the 60 web |
| F7 | PARTIAL | included in the 60 web |
| F12, F13, F14, F16 | PENDING (not started in this session) | — |
| F9, F10, F11 | PENDING | — |

**Suggested next step:** the next cut of F6 and F7 (charts, human body, report form) and then F13, the text assistant with a null `LlmGateway` and an 8 s time limit, which can be tested without Ollama.

### 2026-11-14 · E05 · F6 and F7, second cut (TDD)

**RED → GREEN pass per component.** Each test was run before implementing and failed because of a nonexistent module, or because of the assertion that describes the criterion, depending on the case.

| Module | RED observed | GREEN |
| --- | --- | --- |
| `features/cabin/BodyMap.tsx` (F6.5) | Yes, nonexistent module | 5 tests |
| `features/cabin/CabinPanel.tsx`, waiting state (F6.7) | Yes, 1 test failed on an assertion | 5 tests in the file |
| `features/charts/series.ts` and `LineChart.tsx` (F6.4) | Yes, nonexistent module | 8 tests |
| `features/ship/ZoneCharts.tsx` (F7.3) | Yes, nonexistent module | 5 tests, including the frozen pause |
| `features/ship/ReportForm.tsx` (F7.5) | Yes, nonexistent module | 5 tests. 2 failed because of a wrongly copied type name in the test, and the test was fixed |
| `features/ship/CatalogList.tsx` (F7.6) | Yes, nonexistent module | 4 tests |
| `features/ship/DemoPanel.tsx` (F7.7) | Yes, nonexistent module | 5 tests |

**Quality at the close of E05:**

- `npx vitest run` → `Test Files 22 passed (22)`, `Tests 93 passed (93)`.
- `npx vitest run --coverage` → lines 99.43 %, functions 98.76 %, statements 98.99 %, branches 91.66 %. It exceeds the 80 % threshold in all four metrics.
- `npx tsc --noEmit` → exit 0.
- `npx vite build` → `✓ built in 177ms`, bundle 140.92 kB. It does not change because `App` does not import the new panels yet.
- `npm run codegen` → `✔ Generate outputs`.

**Decisions and deviations of this cut:**

1. **Charts in SVG, not uPlot.** uPlot draws on canvas, and jsdom cannot test it. With SVG the logic is pure and can be tested. When it is tested in a real browser, the engine can be changed without touching `series.ts`.
2. **90 s window and labeled threshold.** The marks (threshold, `ANOMALY`) carry text in addition to the shape, so as not to depend on color.
3. **Pause freezes the readings.** When paused, the chart shows the last snapshot; on resuming it catches up with the readings that arrived.
4. **Body silhouette pending.** The plan asks for an SVG silhouette with six indicators. This cut has the six indicators as buttons in a list; the silhouette is left for later.
5. **Catalog of 6 types, not 61.** `incidentTypes.ts` is a sample with the real shape of the type (plan, section 13.9). The full catalog is a versioned datum that will come from A.
6. **Type name fixed in the test.** The type "Burning smell" is called "Burning smell or overheating" in the plan. The test used the short name; the test was fixed, not the fixture.
7. **Demo mode by profile.** Visible only in `dev1`, `dev2` and `jury`. In any other profile it returns `null`.
8. **`zoneStatus` and empty state:** the dead function from E04 stays removed. The waiting state of the cabin panel is tested in `CabinPanel.test.tsx`.

**What is still undone in F6 and F7:**

- `useWs` hook connected to `/ws` and mounting the panels in `App`. Depends on A (I2).
- Real GraphQL mutations (`acknowledgeAlert`, `reportIncident`, `resolveIncident`). Today the components only emit callbacks.
- Catalog of 61 types and 12 categories (A's data).
- WebSocket and GraphQL error states (6.7): pending with the hook.

**Status:** F6 PARTIAL, F7 PARTIAL. The components and their logic are tested. The wiring with the backend is missing.

**Method note, repeated:** the `stream.ts` piece from E04 had no observed RED. It was not repeated in E05.

### 2026-11-14 · E06 · Wiring of panels in the app

**What:** the app stops being an empty screen. It has two views, Cabin and Facility, connected to a shared state with demonstration data (no backend yet).

**RED → GREEN pass:**

| Module | RED observed | GREEN |
| --- | --- | --- |
| `app/scenario.ts`: pure state (scenarios, zones, tickets, alert, series) | Yes, nonexistent module | 10 tests |
| `ReportForm`: type preselected from the catalog | Yes, 1 test failed on an assertion | 6 tests in the file |
| `App.tsx`: integration of the views | Yes, "Facility" tab not found | 7 tests |

**Flows tested in `App.test.tsx`:** view change; triggering high CO₂ in the laboratory and seeing the alert with "What to do" before the reason; acknowledging the alert; "Normalize everything" returns to normal; reporting from the catalog with the preloaded type and the ticket appears on the floor plan; selecting a zone opens its charts.

**Quality at the close of E06:**

- `npx vitest run` → `Test Files 23 passed (23)`, `Tests 110 passed (110)`.
- `npx vitest run --coverage` → lines 99.55 %, functions 99.08 %, statements 98.81 %, branches 91.89 %.
- `npx tsc --noEmit` → exit 0.
- `npx vite build` → bundle 159.45 kB (gzip 51.83 kB).

**Verification in the browser** (`vite` at 127.0.0.1:5173, stopped when finished):

- Desktop: the full flow works. The laboratory changes to "◆ Alert" with its `INC-0001` pin, the cabin's global status light changes to Alert, and the alert panel appears.
- Problems that were found and fixed:
  1. The floor plan zones were 100 units wide and the names overlapped. They were widened to 130 and the font was reduced to 11 px.
  2. The ticket pin came out black on a dark background. It now uses the theme's text color.
  3. The alert panel was below the human body. It was moved up right below the status light, because the plan asks for the actions first.
  4. At 375 px the floor plan was unreadable. It now has a minimum width of 480 px and scrolls inside its panel.
- At 375 px the cabin has no horizontal scrolling (`scrollWidth = 375`).

**B's decisions in E06:**

1. **Demonstration data, not the backend.** The initial state is `initialState` and the queries to GraphQL and `/ws` arrive at milestone I2. That is why there is no network hook; the components keep receiving props.
2. **Tickets numbered by arrival:** `INC-0001`, `INC-0002`... It is a demonstration code. The backend will assign its own.
3. **Fixed time (`2026-11-14T10:00:00Z`)** in the app. The tests do not depend on the clock.
4. **Demo scenarios:** each one has a severity and a title. Only high CO₂ changes the cabin dashboard and shows the alert with its actions; the others open a ticket and change the zone. It is a simplification that must be reviewed when there is real data.
5. **Pressure and nitrogen marked DEMO** in the zone series: they have no verified source in the plan.
6. **Styles in `shared/layout.css`:** 48 px touch targets, cabin cards in a grid and a scrolling floor plan. It is presentation; it has no automated tests, and it was checked by eye in the browser.

**What is not done:**

- The CO₂ trend in the cabin view (the chart exists, but it is not mounted in the cabin).
- `useWs` hook and connection to `/ws`; real GraphQL mutations.
- The WebSocket and GraphQL error states (6.7).
- Full catalog of 61 types (Dev A's data).

**Status:** F6 PARTIAL, F7 PARTIAL. The screen is wired with demonstration data and was verified on desktop and on a phone.

### 2026-11-14 · E07 · F13 text assistant, and review of the earlier work

**Review on resuming (model change in the session).** Before continuing, the real state was checked: Python 41 tests green, web 110 green and 2 suites in RED on purpose (the assistant's). Findings and what was done:

1. The assistant's use case **did not publish `assistant.answer_ready`** or return the `utterance_id`, and the plan asks for it. It was added with tests.
2. **`npm run lint` was broken:** the script existed but ESLint was not installed. It was installed and no findings remain.
3. The `.gitignore` and the short READMEs of `web`, `knowledge` and `assistant` were missing, which the definition of done requires. Created.
4. This logbook's phase map was out of date (it said "mount the panels in `App`"). Updated.
5. **Correction to E03:** the demonstration catalog has **15 actions**, not 16. It was verified by counting the JSON (`rules 8, actions 15, passages 3`).
6. The project memory said "no code". It was updated and two memories were added (real progress and way of working).

**F13 backend (Python)**

| Piece | RED observed | GREEN |
| --- | --- | --- |
| Knowledge: `DemoKnowledgeSource.search` | Yes, 4 tests failed | 4 tests |
| Knowledge: `KnowledgeQuery` facade | Yes, collection error from import | 1 test |
| Assistant: `AskAssistant` use case and adapters (null, Ollama, memory) | Yes, collection error (nonexistent module) | 10 + 2 tests |
| Assistant: `answer_ready` and `utterance_id` | Yes, collection error (`ListPublisher` nonexistent) | 3 tests |
In the use case, 2 tests failed because of an error **in my test**: it compared `result.text.lower()` with a string that had `mmHg` with a capital H. The test was fixed; the code returned the correct passage.

**F13 acceptance criteria and their evidence**

| Plan criterion | Test |
| --- | --- |
| "Why does my head hurt?" answers with the TB-004 passage and its citation | `test_answers_a_headache_question_with_the_tb004_passage_and_its_citation` |
| Without Ollama, or with more than 8 s, the answer arrives anyway with the passages | `test_falls_back_to_the_passages_when_the_model_exceeds_the_time_limit`, `..._when_the_model_fails`, `test_works_without_any_language_model` |
| A question without a passage does not produce an invented answer | `test_answers_no_information_without_calling_the_model_when_no_passage_is_relevant` |
| The assistant never changes the state of an alert | Structural: it only receives a read port (`ActiveAlerts.titles`). In addition, the `App` integration test checks that after asking, the alert is still active and the Acknowledge button is still there |

**F13 web**

| Piece | RED observed | GREEN |
| --- | --- | --- |
| `mockAnswer.ts` | Yes, nonexistent module | 3 tests |
| `AssistantPanel.tsx` | Yes, nonexistent module | 5 tests |
| `activeAlertTitles` in `app/scenario.ts` | Yes, 3 tests failed | 3 tests |
| Assistant tab in `App` | Yes, 2 tests failed | 2 tests |

**Verification in the browser** (development server, stopped when finished): high CO₂ was triggered in the laboratory, the Assistant was opened and the sample question was tapped. The answer cites TB-004 and TB-003 with their evidence state and names the active alert. Back in the Cabin, the state is still "◆ Alert" and the Acknowledge button is still there. At 375 px there is no horizontal scrolling. Problems that were seen and fixed in `layout.css`: the lines of the answer collapsed into one paragraph, the source links were dark blue on a dark background, and the "Question" label was stuck to the field.

**Quality at the close of E07**

- Web: `npm run lint` with no findings. `npx tsc --noEmit` exit 0. `npx vitest run --coverage` → 25 files and 123 tests green; lines 99.62 %, functions 99.26 %, statements 98.67 %, branches 90.47 %. `npx vite build` → 163.08 kB (gzip 53.02 kB). `npm run codegen` correct.
- Python: `pytest tests` → 44 tests green. `ruff check` and `ruff format --check` clean. Strict `mypy` with no problems in 27 files.

**Decisions and deviations**

1. **TypeScript 7 → 6.0.3.** `typescript-eslint` only supports TypeScript up to 6.0; using `--legacy-peer-deps` would have left a broken tree. With 6.0.3, `tsc`, the build and the tests still pass. `defineConfig` was also moved to `vitest/config` and a triple-slash reference that ESLint flagged was removed.
2. **Demonstration passages paraphrased from the context document, not from the PDFs.** The three passages (TB-004, TB-003, TB-044) come from the context summary, which already marked their state (`TB` or `VERIFIED`). **The PDFs were not opened.** Before presenting them as literal citations they must be verified against the source (it is part of F12).
3. **Temporary duplication in the web.** `mockAnswer.ts` and `data/mocks/passages.ts` replicate the backend's policy and passages until the interface consumes `askAssistant` (I2). If the backend changes, there is a risk of them diverging.
4. **Ollama has not been tested against a real Ollama.** The adapter is tested with a fake opening function that returns NDJSON. There is no model chosen (pending decision) and performance without a GPU was not verified.
5. **The 8 s limit stops waiting, but does not cancel the model's thread.** If the model hangs, the thread stays alive until it finishes. Pending improvement: put the time limit on the adapter's own HTTP request. The tests use a limit of 0.05 s; the default value of 8 s is not run in them.
6. **Active alert:** it is named as `title (severity)` from the open automatic tickets with values still out of range.
7. **Citations outside the model.** The use case puts them, so the model cannot invent a source.

**What is not done in F13**

- GraphQL resolvers (`askAssistant`, `confirmUtterance`, `conversation`): they are registered in the schema that Dev A composes.
- `conversation` and `utterance` tables in PostgreSQL and their migration; today conversations live in memory.
- n8n adapter (optional) and real adapter of `ActiveAlertsQuery`.
- Voice with Whisper and confirmation of what was transcribed (F14).

**Status:** F13 PARTIAL. The text flow works end to end with demonstration data and is tested.

### 2026-11-14 · E08 · First commit and branches on GitHub

**What:** Dev B's work was pushed to GitHub (`https://github.com/Julio-Cuellar/SpaceOverflow`).

- **Previous state:** the directory was already a repository (someone on the team initialized it while work was going on) with a single commit, `2d38c34 first commit`, which only had a `README.md`. `main` was in sync with `origin/main`. Up to here this logbook said it was not a repository; that is no longer true.
- **Branches created:** `dev-B`, `dev-A` and `testing`. **Git does not allow spaces in branch names**, so `dev B` and `dev A` are called `dev-B` and `dev-A`.
- **Contents:** `dev-B` has commit `4babd3c` with 109 files (`web` 67, `src` 29, `tests` 8 and the root ones). `dev-A` and `testing` are at `2d38c34`, the same as `main`, without changes; they are ready for Dev A and the tests to work on.
- **Before pushing:** it was checked that no secret or large file went in. The scan only found false positives (the word `token` in the CSS design tokens). No file exceeds 500 KB. `node_modules`, `.venv`, `dist`, `coverage` and the caches are in `.gitignore`.
- **Verification on GitHub** (not just in the terminal): `git ls-remote` and the GitHub API show the three branches and `dev-B` at `4babd3c`, with 110 files (the 109 plus the `README.md`).

**For whoever clones the repository:**

- The types in `web/src/data/graphql/generated/` are **not versioned**. They are generated with `npm run codegen`. No test imports them, so `npm install` and `npm test` are enough.
- The Python environment (`.venv`) is not versioned either: it must be created and `pydantic`, `pytest`, `ruff` and `mypy` installed. `pyproject.toml` lists the dependencies.

**Pending item that can now be done:** CODEOWNERS and F0's CI job (previously blocked for lack of a repository).

**Status:** F0 is still PARTIAL. All it lacks is CODEOWNERS and CI.

### 2026-11-14 · E09 · F12 RAG over NASA PDFs, and GitHub Actions CI

**Limit of this stage:** the whole pipeline was built and tested with **synthetic** PDFs. **No real PDF was downloaded.** Downloading files requires explicit permission, and it was requested with name, source and size. With `HEAD` requests (which do not download) it was verified that the 7 URLs answer `200 application/pdf` and add up to **14.56 MB** (the Vol. 2 standard weighs 6.56 MB; the rest, between 0.38 and 1.87 MB). That is why **there is no real ingestion or real evaluation yet**.

**F12: RED → GREEN per piece** (51 new tests; Python goes from 44 to 95)

| Piece | RED observed | GREEN |
| --- | --- | --- |
| Document and license manifest (`ingest/manifest.py`) | Yes, collection error | 6 |
| Fragmentation by requirement (`ingest/chunking.py`) | Yes, collection error | 8 |
| PDF reading (`ingest/pdf.py`) | Yes, collection error | 3 |
| Store, idempotent ingestion and command (`ingest/store.py`, `pipeline.py`, `__main__.py`) | Yes, collection error | 11 |
| RAG search, glossary and fallback to demo (`rag_source.py`, `domain/glossary.py`) | Yes, collection error; 10 of 12 then failed because of the missing glossary | 12 |
| Evaluation (`evaluate.py`) and questions | Yes, collection error | 11 |

**How PDF reading was tested without downloading anything:** `tests/knowledge/pdf_helpers.py` builds a minimal valid PDF (with a cross-reference table) and `pypdf` reads it back.

**A gap that was found and closed properly:** when evaluating the glossary, a test failed because the question about aerobic capacity received no translation. On seeing the detail, others passed only through an incidental translation (for example "astronaut" → `crew`, without translating "bone density"). The minimum to make it pass was not added: 13 entries were added and the "vibrar" form with the real terms (`aerobic capacity`, `bone density`, `partial pressure`, `rate of change`, etc.).

**F12 guarantees and their evidence**

| Plan criterion | Test |
| --- | --- |
| No PDF is packaged without a confirmed license | `test_no_document_is_packageable_until_its_license_is_confirmed`, `test_rejects_a_manifest_that_packages_...` |
| Idempotent ingestion: rerunning it does not duplicate | `test_running_it_twice_does_not_duplicate_anything` |
| Each fragment keeps document, requirement, page and state | `test_splits_a_page_at_each_requirement_reference` |
| Without a relevant passage there is no answer | `test_returns_nothing_when_no_passage_is_relevant` |
| Ingestion runs without internet | The command only reads local files and downloads nothing |
| A PDF without text (a scan) is flagged, not ignored | `test_a_pdf_without_extractable_text_is_flagged_instead_of_ignored` |
| Zero answers without a source in the evaluation | `test_an_out_of_scope_question_must_not_get_any_passage` (the real measurement waits for the PDFs) |

**Decisions and limitations of F12**

1. **Language was a problem the plan did not foresee.** The NASA documents are in English and the questions in Spanish; a term search would not find "headache" from "dolor de cabeza". Provisional solution: a **Spanish-English glossary** (`data/knowledge/glossary_es_en.json`, 40 entries) that expands the question. It is a limited solution: a term that is not in the glossary is not found. The underlying solution is a multilingual embeddings model, which is pending decision no. 5. **The glossary is pending the team's review.**
2. **The score weights by rarity** (`ln(1 + (N+1)/df)`) and requires a minimum of 1.0: a word that is in almost all fragments is not enough to return a passage.
3. **Possible evidence inconsistency, to be decided.** The RAG takes the evidence state from the document type: all Technical Briefs come out as `TB`. But the demonstration catalog marks the TB-003 hypoxia passage as `VERIFIED`, following the context document. I did not change it because that classification is the team's. When the real PDFs are ingested, the same text would come out as `TB`.
4. **The evaluation questions are hypotheses.** The expected documents come from the context document, not from having read the PDFs. They must be refined after the first real ingestion. There are 16 in scope and 2 out of scope.
5. **The PDFs and their index are not versioned** (`data/knowledge/pdfs/`, `data/knowledge/index/` in `.gitignore`): the redistribution license is not confirmed.
6. **Tables that come as images are not extracted** (for example Table 6.2-1). The plan asks to transcribe them by hand; it is not done.
7. **The per-profile selector is not wired.** The classes (`RagKnowledgeSource`, `FallbackKnowledgeSource`) exist and are tested, but whoever assembles the application is `main.py`, which is Dev A's.
8. **`pyproject.toml`:** `pypdf` was added and the development dependencies moved to `[project.optional-dependencies]`, so that the CI installs with `pip install -e ".[dev]"`.

**GitHub Actions CI** (`.github/workflows/ci.yml`) and **CODEOWNERS** (`.github/CODEOWNERS`)

- **It runs** on every pull request and on every push to `main`, `dev-A`, `dev-B` and `testing`. Read-only permissions; a new push cancels the previous run of that branch.
- **`web` job:** `npm ci`, lint, types, coverage (fails below 80 %), build and codegen.
- **`python` job** on 3.12 and 3.14: `pip install -e ".[dev]"`, `ruff check`, `ruff format --check`, `mypy` and `pytest`.
- **Verification in a clean copy** (clone of `dev-B` in a temporary folder, without my `node_modules` or my `.venv`): the 6 `web` steps pass (line coverage 99.62 %) and the 5 `python` steps pass on 3.14 (95 tests).
- **What could NOT be verified:** Python 3.12 is not installed on this machine. It was only checked that the 52 files parse with the 3.12 grammar and that `mypy --python-version 3.12` gives no problems. The real run on 3.12, and the CI on a GitHub runner, happen for the first time when this branch is pushed. If 3.12 fails, it is fixed.
- **Finding during verification:** until now the build had been checked with `npx vite build`, not with the real script (`tsc -b && vite build`). The real script was run and it passes.
- **CODEOWNERS** only covers Dev B's folders. Dev A's GitHub user is missing (it was left noted as pending in the file itself).

**Status:** F12 PARTIAL (pipeline tested; the real ingestion and evaluation are missing). CI and CODEOWNERS created; their first run on GitHub is pending.

### 2026-11-14 · E10 · F12 with the real PDFs: download, ingestion and evaluation

**Permission:** the user authorized, with name, source and size, the download of the 7 PDFs (14.56 MB). They were downloaded to `data/knowledge/pdfs/` (ignored by git) and it was checked that all 7 start with `%PDF-`. Nothing else was downloaded.

**Real ingestion:** 2,087 fragments (Vol. 2: 1,456; Vol. 1: 291; TB-002: 116; TB-003: 76; TB-004: 56; TB-044: 52; medical kit: 40). Only 665 carry a requirement reference: the rest is text from tables, lists and sections without their own `[V# ####]`.

**Defects that only appeared with the real PDFs** (each one was reproduced with a test in RED before fixing it)

| Defect | Cause | Fix |
| --- | --- | --- |
| A citation inside a sentence split the fragment | `[V2 6004]` preceded by a lowercase letter, "(" or "," is an inline citation, not the start of a requirement | `_starts_a_requirement` |
| Old fragments stayed in the index after changing the cutting rules | The ids change when cutting differently; ingestion only adds | `--rebuild` option (rebuilds in memory and replaces atomically; if nothing was indexed, it keeps the previous index) |
| A table that lists "headache" among dozens of terms beat a focused passage | The score counted matches without normalizing by length | BM25 (K1 1.5; B 0.75) |
| "dura" → `lasts`, but the text says `last` | Normalization of plurals and third persons was missing | `stem` |
| With 500 characters of excerpt the figure was left out in half the cases | Cut at the start of the fragment | The excerpt is the whole fragment (≤ 1,200) |
| "Who won the last football world cup?" received an answer | It matched only on "world", inside a list of acronyms | At least 2 matching terms are required (with 1 question term, 1) |
| Titles and index entries came out as passages | Fragments of 2 or 3 words | Those with fewer than 6 content words are discarded |
| A cross-reference after a digit ("…Volume 1 [V1 4030] Title)") split V1 4033 and the 1.3 mSv/day figure was cited as V1 4030 | The "page number" rule took it for a requirement | Inside an unclosed parenthesis it is a citation (RED test observed; 120 tests pass) |
| The evaluation command failed with a traceback if a file was missing | — | Clear message and exit code 2 |

**How it was evaluated (and why it was changed)**

- My questions from entry E09 were hypotheses based on the context document (they expected a specific document). They were replaced by **content anchors**: text that must appear in the returned passage, verified by hand in the PDFs' raw text.
- A **held-out validation** set was added (`eval_questions_validation.json`, 9 + 1 out of scope). **The code is not tuned by looking at that set**: it serves to measure whether what was fixed generalizes.
- An **English** set was added (`eval_questions_en.json`, 25 + 3 out of scope), diagnostic: it separates translation failure from search failure.
- The metric is **strict**: it hits only if in the top 3 there is a passage with the anchors (and, if requested, the document).

**Measured results** (k = 3, index of 2,087 fragments)

| Set | Hits | Out-of-scope answered |
| --- | --- | --- |
| Main, Spanish (16 + 2) | 9 of 16 (56 %) | 0 of 2 |
| Held-out validation, Spanish (9 + 1) | **1 of 9 (11 %)** | 0 of 1 |
| Diagnostic, English (25 + 3) | 13 of 25 (52 %) | 0 of 3 |

The plan's threshold (80 %) **is not met** and the evaluation command exits with code 1. The threshold was not lowered nor were the questions adjusted to make it pass.

**Honest reading of the numbers**

1. **Zero answers without a source:** no out-of-scope question received a passage (0 of 6 across the three sets: 2, 1 and 3 out-of-scope cases). It is the criterion that matters most for not inventing protocols, and it is met.
2. **Retrieval is weak.** The English set also fails half the time: the problem is not only the language. It is lexical search over a document of ~300 pages with technical vocabulary: a paraphrase ("daily energy" versus *energy requirements*) or a figure in a table is not found by word matching.
3. **The gap between 56 % and 11 %** is the expected overfitting: the glossary (40 entries) was tuned by looking at the main set. The held-out set shows the performance without that tuning, and that is the number to believe.
4. **Concrete failures** (position of the correct passage in the ranking, in an intermediate measurement): headache, rank 21; CO₂ symptoms, 27; minimum cabin pressure, 19; medical kit, 26.

**Verified against the source text** (by querying the indexed fragments)

- Sleep noise: `[V2 6079]` and NC-40, for missions longer than 30 days (Vol. 2, p. 98). It matches the context document. The row of the summary table (p. 94) cites "V2 6077; V2 6078; V2 6080; V2 6083" because it groups other limits: it is not a discrepancy.
- The context's key figures (1.3 mSv/day, 600 mSv career, 250 mSv per solar event, 80 % aerobic capacity, 95 % bone, 30 % diluent, 95 dBA in alarms) appear in the indexed text with the requirement numbers that the context indicates in the nearby text. Long fragments rarely carry their own requirement in their `requirement_ref` field (most figures are in fragments without it), so **the citation comes out with document and page, not always with a requirement number.**
- **Open limitation, not fixed:** if the title of the section that precedes `[V1 4033]` ends in lowercase ("…Galactic Cosmic Radiation [V1 4033]"), the rule takes it for a citation and the requirement is left without `requirement_ref` (Vol. 1, p. 44). Before the parenthesis fix that figure was cited with the wrong number (V1 4030); now it is cited without a number, which is more honest, but incomplete.

**Decisions left for the team (I did not take them)**

1. **Multilingual embeddings model** (pending decision no. 5). It is the underlying solution to weak retrieval. It costs: downloading a model (requires explicit permission), heavy dependencies (PyTorch or ONNX), and packaging it offline in Docker. Cheap and partial alternative: extend the glossary by reviewing it with the team, knowing that it does not generalize.
2. **Evidence state.** The RAG gives `TB` to every Technical Brief; the demonstration catalog marks TB-003 as `VERIFIED`. It must be decided which one applies.
3. **Glossary review** (40 entries, mine, not reviewed by anyone on the team).
4. **License of the PDFs:** still `unverified`; that is why nothing is packaged or versioned.

**What did not change:** the assistant still does not decide alerts and only answers with cited passages; when in doubt it does not answer ("no information"). The retrieval weakness translates into **not answering more often than it should**, not into inventing.

**What is still undone in F12:** passage search in the web (12.6), tables as images not transcribed, source selection by profile (depends on `main.py`, Dev A's).

**Status:** F12 PARTIAL. Real ingestion and evaluation done; the plan's retrieval threshold (80 %) is not met.

**Verification at close:** 120 Python tests pass; strict `ruff check`, `ruff format --check` and `mypy` clean.

## E11 · Human Integration Design Handbook (Nov 15, 2026)

**What was done:** with the user's explicit permission the Handbook (rev. 1, 25.3 MB, `nasa.gov`, valid PDF) was downloaded to `data/knowledge/pdfs/`, ignored by git. It was indexed with `--include-optional` (the manifest marks it optional, `UNVERIFIED`, license `unverified`; it was not modified).

**Result:** it contributes 3,261 fragments (5,347 in total) and **worsens** retrieval: main 9→8 of 16, validation 1 of 9 unchanged, EN 13→12 of 25. No answers to out-of-scope questions in any set.

**Cause:** the Handbook weighs more than the rest together and its passages similar to the standard's displace the correct one from the top 3. It is the same limit of lexical search, not a fault of the PDF. The quality of its text (tables, columns) was not reviewed.

**Decision:** the index stays **without** the Handbook (2,086 fragments). Including it is opt-in. Re-evaluate when there are embeddings, or weight by document.

**Correction:** in the previous report the out-of-scope questions were given as "0 of 6" per set; they are 2, 1 and 3 cases (6 across the three). README and logbook corrected.

## E12 · Integration with Dev A's branch (Nov 15, 2026)

Working branch `integration/a-b`, cut from `dev-B` (ec2e298). Local backup tag `backup/dev-B-pre-integracion` (pre-integration). Decisions that were taken by default when executing the plan, in the absence of an explicit answer: D1 new rules only with the 15 existing actions and `DEMO` unless there is a verified citation; D2 Python `>=3.12,<3.13` like A; D3 new PR to `testing`; D4 A's `main.py` is not edited, the call to `register_knowledge` is requested from them.

### Phase 0 · Measured baseline (without touching code)

- **Download authorized by the user:** `uv` 0.13.8 (pip, in a separate environment outside the repository) and Python 3.12.16 (downloaded by uv), plus A's dependencies (`uv sync`). None of this is versioned.
- **A's tests, in a copy of `origin/dev-A` (9fb8bfe):** 293 pass in 79 s with Python 3.12 and Docker (testcontainers with `pgvector/pgvector:pg16`). It matches what their logbook says.
- **My tests on `dev-B`:** 120 Python and 123 web pass.
- **What was read from A:** the handlers are `handler(envelope, ctx)`; publishing is done with `ctx.publish(EventEnvelope.from_payload(payload, aggregate_type, aggregate_id, partition_key, correlation_id, causation_id))`; Monitoring uses `aggregate_type="alert"`, `aggregate_id=alert_id`, `partition_key="habitat:<id>"` and `causation_id` = causing event. Their contract test (`tests/contract/test_event_contracts.py`) has a fixed list of 22 events and one sample per event.

### Phase 1 · Mechanical merge of `origin/dev-A` (9fb8bfe)

- **Conflicts (5) and resolution:** `.gitignore` union of both; `pyproject.toml` A's base plus `pypdf>=5` (Python `>=3.12,<3.13`, hatchling, uv dependency groups); `knowledge/contracts.py`, `knowledge/facade.py` and `assistant/contracts.py` keep my version plus a **provisional** `EVENTS = {}` so that A's event registry imports. `uv.lock` regenerated (`pypdf` 7.1.0).
- **Formatting adjustments, without changing behavior:** A's ruff configuration enables `E501` and `RUF100`; 10 long lines of mine were split and a `noqa: BLE001` that A does not enable was removed.
- **Verification on Python 3.12.16:** ruff and `ruff format` clean; strict mypy with no errors in 135 files; **import-linter: 4 contracts kept, 0 broken** (my modules meet A's independence and layers without changes); pytest **405 pass and 8 fail**.
- **The 8 failures are phase 2's test in RED**, all in `tests/contract/test_event_contracts.py`: the registry does not have the `knowledge.*` or `assistant.*` events because my `EVENTS` is empty on purpose. Counts: 293 from A − 8 + 120 mine = 405.

### Phase 2 · Contracts aligned with Dev A's (TDD)

- **RED observed:** the 8 failures from phase 1 plus 2 collection errors in new tests (`cannot import name 'RecommendationEnriched'` and `No module named 'spaceapp.modules.knowledge.adapters.inbound'`), both because of the missing implementation.
- **GREEN:** `uv run pytest` → **422 pass** (293 from A + 129 mine); ruff, strict mypy (137 files) and import-linter (4 kept, 0 broken) clean.
- **Changes:**
  - `knowledge/contracts.py` and `assistant/contracts.py`: `RecommendationReady`, `RecommendationEnriched` and `AnswerReady` are `EventPayload`s (`extra="forbid"`, `event_type`), with `EVENTS`. My copy of `AlertRaised` was deleted: the use case imports the one from `monitoring.contracts`, so there is no drift.
  - The citation is `platform.vocab.Citation` (fields identical to my `CitationDTO`); `CitationDTO` remains as an alias of the same type.
  - `HandleAlertRaised.handle(envelope, ctx)` is asynchronous like A's. It publishes with `ctx.publish(EventEnvelope.from_payload(...))`: `aggregate_type="recommendation"`, the same `partition_key` as the alert, `causation_id` = the alert's event and `correlation_id` inherited or, if there was none, the alert's id. The `EventPublisher` port and Knowledge's `ListPublisher` were removed. `process` returns `RECORDED` or `DUPLICATE`.
  - `knowledge/adapters/inbound/events.py`: `register_knowledge(bus, handler)` subscribes `monitoring.alert_raised` with the consumer `knowledge.on_alert_raised`.
- **New tests:** walk through A's `InMemoryEventBus` (alert → recommendation with citations, same event twice → one, unknown rule → visible failure in `bus.failures` and the event stays unmarked), causal and correlation chain, and rejection of an event of another type.
- **Limits that remain (not of this phase):**
  - `main.py` is A's and still does not call `register_knowledge`: it is requested from them (D4).
  - With the real outbox relay, the recommendation is saved in memory, not in PostgreSQL, so it does not survive a restart. A SQL repository is missing (own module, `knowledge` schema).
  - `AnswerReady` is already an `EventPayload`, but the assistant still publishes through its own port; an adapter toward the bus is missing.

### Phase 3 · Catalog of 25 rules (TDD)

- **The gap:** Monitoring (A) emits 25 rule keys; my demo catalog knew 8 and only 3 matched (`env-co2-1h`, `env-dpdt`, `env-n2`). For the other 22 the handler would have raised `UnknownRuleError` and the event would have ended as failed in the outbox.
- **RED:** `tests/knowledge/test_rule_coverage.py` (crosses `rules/catalog/monitoring.json` with my catalog) → **96 tests fail**: 22 rules without a recommendation, 5 rules of mine that Monitoring never emits (`env-pio2`, `env-ptotal`, `env-rh`, `env-t`, `env-tendencia`) and the dependent ones. The old test `test_the_catalog_covers_the_rules_of_the_plan`, which fixed the old keys, was deleted.
- **GREEN:** `tests/knowledge` → 237 pass, 19 skipped on purpose (rules without a requirement number or with fallback; they do not apply to that case).
- **What the crossing tests guarantee:** every Monitoring rule has a recommendation; there are no orphan rules; the action that Monitoring names (`action_key`) is among the recommended ones and exists in the action catalog; **no citation claims more evidence than its rule** (order DEMO < UNVERIFIED < TB < VERIFIED); the requirement that Monitoring names is the one cited; a DEMO rule only has DEMO citations.
- **How the content was written:** a script (outside the repository) generates the 22 new rules from A's catalog: the text comes from its thresholds, operators and units; the citation comes from its `source_document`, `source_requirement` and `evidence_state` (the `excerpt` is A's description, not a literal quote); the 3 rules that already had curated text and citation are kept. The `severity` field was removed from my catalog (nobody used it and severity belongs to A's rule).
- **Actions:** each rule carries A's action plus a second action from those that already existed, by group (CO₂, low/high PIO₂, pressure, N₂, humidity, temperature, trend). **2 actions were added** because A names them and they did not exist: `verify_airtightness_and_seals` and `check_sensor_and_trend` (demonstration text, similar to the existing ones, without medical content). This departs from what D1 planned ("only the 15 existing"): without them, 8 of A's rules were left without their action.
- **Honesty:** 16 of the 25 rules have DEMO backing in A (the humidity, temperature, pre-alert and trend thresholds do not come from the standard); their recommendations come out `DEMO`.

### Phase 4 · Full verification

- **New test against the real outbox** (`tests/integration/knowledge/test_alert_to_recommendation.py`, PostgreSQL with testcontainers): an alert published with `UnitOfWork` → A's relay delivers it → Knowledge publishes `knowledge.recommendation_ready` in the outbox, and both rows end up `done`; an alert of an unknown rule stays `pending` with `attempts=1` and the error recorded. **There was no RED:** it verifies behavior already implemented in phase 2, it adds no new behavior.
- **Results** (equivalent to `scripts/check.sh`, on Python 3.12.16): ruff and format clean; strict mypy in 137 files with no errors; import-linter 4 kept, 0 broken; **547 tests pass** and 19 are skipped on purpose; **coverage 97.27 %** (minimum 80 %).
- **The RAG did not change:** re-ingestion with `--rebuild` (2,086 fragments) and the three evaluations give the same as before: 9 of 16, 1 of 9 and 13 of 25; no out-of-scope question answered.
- **Web:** 123 tests pass (25 files).

### Phase 5 · CI and close

- **CI:** the Python job stops using `pip install -e ".[dev]"` (the extras no longer exist after taking A's `pyproject.toml`) and the 3.12 + 3.14 matrix. Now: Python 3.12, `pip install uv==0.13.8`, `uv sync --frozen` (fails if `uv.lock` does not match), `ruff check`, `ruff format --check`, `mypy`, `lint-imports` and `pytest --cov --cov-fail-under=80`. The GitHub runner comes with Docker, which A's integration tests and mine need.
- **Rehearsal in a clean copy** (worktree of `HEAD`, `uv sync --frozen`): ruff, format, strict mypy (137 files) and import-linter (4 kept) clean; 547 tests pass, 19 skipped; coverage 97.27 %. **What has not been seen:** the first real run on GitHub Actions (`uv` version, the runner's Docker).
- **Unresolved finding:** there are two `CODEOWNERS`, A's at the root (with example `@dev-a` and `@dev-b`) and mine in `.github/` (with the real user). GitHub gives priority to `.github/CODEOWNERS`, so the root one is not used until they are unified. I did not touch it: the root one is A's.
- **Pending with Dev A:**
  - That `build_registry` in `main.py` calls `register_knowledge` (Knowledge does not receive alerts until then).
  - `source_kind` (DEMO) does not travel in `recommendation_ready`; it is still an open request.
  - A SQL repository of recommendations (`knowledge` schema) so that they survive a restart.
- **Pending on my side:** adapter of `assistant.answer_ready` toward the bus, passage search in the web, and the embeddings decision.
