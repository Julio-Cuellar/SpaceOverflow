# Dev B tasks · interface, knowledge and RAG

> NASA Space Apps 2026 · astronaut health monitor
> Working document for **Dev B**. It derives from [`plan-arquitectura.md`](plan-arquitectura.md) (mostly sections 5, 8, 10, 13 and 16) and from [`spaceapps-health-monitor-context.md`](spaceapps-health-monitor-context.md).
> Interactive artifact with the split, the diagrams and the interface prototype: https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8
> Status: **proposal, pending confirmation of the plan**. The hours are work per person, not clock time.
> Language: translated from Spanish to English on 15 Nov 2026 (the interface texts of the plan, such as "Prototipo de apoyo a la decisión", are now English too). Names of shared data (`VERIFICADO`, `jurado`, rule and action keys) keep their Spanish form.

---

## 0. Summary

| | |
| --- | --- |
| **Role** | Owner of the whole interface (SPA) and of the `knowledge` and `assistant` modules. **The whole RAG is theirs.** |
| **Hours** | 34 h in total. 18.5 h in the P0 cut and 15.5 h in P1 and P2 |
| **RAG** | 15 h split in five phases: F8, F12, F13, F14 and F16 |
| **Phases** | F0 (joint), F6, F7, F8, F12, F9 (joint), F13, F14, F10 (interface), F11 (interface) and F16 |
| **Languages** | TypeScript (React) in `web/`. Python (FastAPI) in the `knowledge` and `assistant` modules |
| **Partner** | Dev A: platform, telemetry, monitoring, ship and incidents, crew, missions, Earth link and GraphQL and WebSocket gateway |
| **Golden rule** | B does not depend on A until milestone I2. Until then B works on mocks generated from the contract |

### Dev B timeline

| Hours | Phase | Name | Priority | Effort | RAG |
| --- | --- | --- | --- | --- | --- |
| 0 to 1 | F0 | Foundations (joint with A) | P0 | 1 h | |
| 1 to 7 | F6 | Cabin interface | P0 | 6 h | |
| 7 to 14 | F7 | Ship panel | P0 | 7 h | |
| 14 to 17 | F8 | Knowledge with demo data | P0 | 3 h | RAG |
| 17 to 21 | F12 | RAG over NASA PDFs | P1 | 4 h | RAG |
| 21 to 22.5 | F9 | Delivery for the jury (joint) | P0 | 1.5 h | |
| 22.5 to 25.5 | F13 | Assistant: text and Ollama | P1 | 3 h | RAG |
| 25.5 to 28.5 | F14 | Voice with Whisper | P1 | 3 h | RAG |
| 28.5 to 30 | F10 | Tasks (interface) | P1 | 1.5 h | |
| 30 to 32 | F11 | Control center panel (interface) | P1 | 2 h | |
| 32 to 34 | F16 | Alexa as a fallback | P2 | 2 h | RAG |

F12 is marked P1 in the plan, but it **fits before the delivery** without delaying milestone I6. Raising it to P0 is a pending decision (section 11).

### Milestones in which B takes part

| Milestone | Hour | What B does |
| --- | --- | --- |
| I0 · Contracts frozen | 1 | Reviews and accepts the GraphQL schema, WS messages and OpenAPI. Leaves mocks and type generation ready |
| I1 · Real outbox | 4 | Replaces the in-memory bus with the real outbox in the Knowledge handlers (when F8 exists) |
| I2 · Live readings and simulator | 11 | Connects the WebSocket ticks to the cabin panel |
| I3 · Live incidents | 16 | Connects the ship panel to `ship`, `incidents` and `incident.*` |
| I4 · Alert with a cited recommendation | 17 | Knowledge receives the real `alert_raised` and publishes `recommendation_ready`. It shows in the alert panel |
| I5 · Full GraphQL and WebSocket | 20 | Removes all the mocks. First end-to-end test |
| I6 · Delivery for the jury | 22.5 | Tests the image without internet on another computer |
| I7 · P1 complete | 32 | Plan from Earth end to end, on the interface side |

---

## 1. Scope

### 1.1 What belongs to B

- **Complete SPA** in `web/` (React, Vite and TypeScript): cabin panel, ship panel, tasks of the day, assistant, link and privacy, and control center panel (`/ground`).
- **`knowledge` module:** documents, fragments with citation, action catalog, recommendations, ingestion and search.
- **`assistant` module:** conversations by text and voice, answers with citation and in streaming.
- **Local adapters:** Ollama (wording), Whisper (voice) and Alexa (fallback, demo only).
- **GraphQL resolvers** of Knowledge and Assistant, and the REST routes for audio (`R2`) and Alexa (`R3`).
- **Their part of the Docker image:** serving the SPA and isolating the heavy dependencies of the RAG.

### 1.2 What does not belong to B

- Monitoring rules, PIO₂ calculation, windows and anomaly detection: they belong to the `monitoring` module (A). **The interface shows what the backend computes and does not recompute it.**
- Outbox, relay, inbox and `UnitOfWork`: they belong to the platform (A).
- Simulator, readings ingestion and scenarios: telemetry (A).
- Tables `habitat`, `zone`, `incident`, `task`, `task_template` and the link ones: they belong to A. B consumes them through GraphQL.
- The `/ws` gateway and the composition of the GraphQL schema: A. B registers its resolvers and consumes the messages.

### 1.3 Project rules B must always respect

1. **The language model never decides an alert.** B only explains, and never blocks an alert waiting for Ollama.
2. **Every figure without a verified source is labeled `DEMO`.** Body data also carries the "simulated" mark.
3. **Permanent banner:** "Decision-support prototype. It is not a medical device".
4. **Color never goes alone.** Every state carries a shape, an icon and text: ● Normal, ▲ Attention, ■ Critical.
5. **A medical protocol is never invented.** If there is no passage that supports the answer: "I don't have that information in the loaded sources".
6. **Nothing is executed by voice without confirming** what was transcribed, and there is always text input.
7. **An emergency never depends on the astronaut speaking.** The alert comes from the sensors.
8. Interface texts and documentation in **English** (originally Spanish; changed on 15 Nov 2026).
9. **Alexa is not autonomous**: this is said so in the interface and in the presentation.

---

## 2. How B works without waiting for A

### 2.1 Contract-first

In Phase 0 the following are frozen, between the two:

- **Events** in `contracts.py` (versioned Pydantic models).
- **GraphQL schema** (`schema.graphql`) with types, enumerations and result unions.
- **WebSocket messages** (`ws-messages.schema.json`).
- **OpenAPI** of the REST routes.

A contract change requires review by the other developer. Any change breaks B's build immediately because of the type generation.

### 2.2 Mocks for the interface

- **GraphQL:** simulated server with MSW, generated from the schema, with fixtures per scenario (normal, high CO₂, pressure leak, humidity, O₂ failure).
- **WebSocket:** player of recorded messages (`web/src/data/mocks/ws/*.json`). The recordings come from the artifact's scenarios: ticks at 1 Hz, `alert.raised`, `zone.status`, `incident.opened`, etc.
- **They are removed** at milestones I2, I3 and I5, as A delivers the real thing.

### 2.3 In-memory bus for Knowledge

A delivers in F0 an `InMemoryEventBus` with the same `EventBus` interface as the outbox. B develops the `alert_raised` handler on it and swaps it for the real one in I1. The handlers must be **idempotent** from the start (inbox by `(consumer, event_id)`).

### 2.4 Folder structure

```text
web/
  src/
    app/                    # routes, providers, layout
    shared/
      ui/                   # Evidence badge, SevPill, Gauge, Card, Banner
      lib/                  # severity.ts, evidence.ts, format.ts
      tokens.css            # semantic colors, light and dark theme
    features/
      cabin/                # cabin panel, human body, alert panel
      ship/                 # plan, tickets, per-zone charts, catalog
      tasks/                # tasks of the day, new task
      assistant/            # chat, voice, citations, passage finder
      link/                 # link and privacy
      ground/               # control center panel
    data/
      graphql/              # .graphql documents and generated types
      ws/                   # useWs(topics), queue, resume
      mocks/                # MSW handlers and WS recordings
  codegen.ts, vite.config.ts, vitest.config.ts

src/spaceapp/modules/knowledge/
  domain/  application/  ports/
  adapters/inbound/       # events.py (alert_raised), graphql.py
  adapters/outbound/      # sql.py, demo_source.py, rag_source.py, ollama.py
  contracts.py  facade.py
src/spaceapp/modules/assistant/
  domain/  application/  ports/
  adapters/inbound/       # rest.py (audio), alexa.py, graphql.py
  adapters/outbound/      # sql.py, whisper.py, ollama.py
  contracts.py  facade.py
migrations/knowledge/  migrations/assistant/
data/knowledge/         # demo fragments and document manifest
```

### 2.5 Conventions

- **Branches:** `b/<phase>-<topic>`, under 2 h. Merged to `main` with green CI.
- **B's CI:** `eslint`, `tsc --noEmit`, `vitest`, type generation from the schema, `ruff`, `mypy`, `import-linter` and `pytest` of its modules.
- **`CODEOWNERS`:** `web/`, `modules/knowledge/`, `modules/assistant/`, `migrations/knowledge/` and `migrations/assistant/` are B's.
- **Boundaries between modules:** B only imports from another module its `contracts` and its `facade`. Never `domain`, `adapters` or SQL models.
- **One PostgreSQL schema per module** and no foreign keys to other modules (only soft references by id).

---

## 3. Phases in detail

Each phase states objective, hours, dependencies, tasks with their estimate, acceptance criteria and tests. The checkboxes serve for tracking.

### F0 · Foundations (joint with A) · 1 h · P0

**Objective:** leave the repository, the contracts and the tools ready to work in parallel. A carries the repository and the `InMemoryEventBus`. B carries `web/` and the mocks.

**Depends on:** nothing.

**B's tasks**

- [ ] **0.1 `web/` project (0.25 h):** Vite, React 18, strict TypeScript, ESLint, Vitest and path aliases.
- [ ] **0.2 GraphQL client and type generation (0.25 h):** urql, `graphql-codegen` reading `schema.graphql`. The `npm run codegen` command fails if the contract changes without updating the documents.
- [ ] **0.3 Mocks (0.25 h):** MSW with a `dashboard` handler and a sample WS message player.
- [ ] **0.4 Contracts and review (0.25 h):** review with A the schema, the events and the WS messages. Register `CODEOWNERS` and B's CI job.

**Acceptance criteria**

- `npm run dev` opens an empty screen with the permanent banner.
- `npm run codegen` generates types without errors.
- The mock returns a sample `dashboard` and the player emits a `telemetry.tick`.
- The schema, the events and the WS messages are marked as **frozen (I0)**.

---

### F6 · Cabin interface · 6 h · P0

**Objective:** for the astronaut to understand their state at a glance and be able to act on an alert.

**Depends on:** F0. **Mock:** simulated GraphQL server and recorded WS messages.

**Contracts it consumes**

| Channel | Operation or message |
| --- | --- |
| GraphQL | `dashboard`, `readings`, `alerts`, `alert`, `rules`, `crewMember`, `acknowledgeAlert` |
| WebSocket | `telemetry.tick`, `alert.raised · alert.updated · alert.resolved`, `recommendation.ready · recommendation.enriched`, `scenario.changed`, `groundlink.state`, `subscribe`, `resume`, `ping` |
| REST | `POST /api/v1/sim/scenarios/{key}:start · :stop` (demo mode) |

**Tasks**

- [ ] **6.1 Shell, theme and base components (0.5 h)**
  - Design with semantic tokens (traffic light, evidence, surface) in light and dark. Dark by default for the cabin.
  - Components: `EvidenceBadge` (`VERIFICADO`, `TB`, `DEMO`, `SIMULADO`), `SevPill` with icon (● ▲ ■), `Card`, `Gauge`, `Banner`.
  - Permanent banner "Decision-support prototype. It is not a medical device" and mark "Simulated data".
  - Touch targets of 48 px or more, AA contrast and visible focus.
- [ ] **6.2 Data layer and real time (0.75 h)**
  - `useWs(topics)` hook: single connection to `/ws`, `subscribe`, queue per topic and deduplication by `seq`.
  - **Resume:** stores the last `seq` and sends `resume { after_outbox_id }` on reconnecting.
  - Bar "Reconnecting... showing the last data from N s ago".
  - Coalescing of `telemetry.tick`. **Alerts are never dropped.**
- [ ] **6.3 Cabin panel (1.25 h)**
  - Global traffic light with the worst severity.
  - Cards: oxygen (PIO₂ with gauge and bands), CO₂ (ppCO₂), pressure and rate of change, radiation and Earth link chip.
  - Each value shows its evidence state. The yellow bands, which are the team's proposal, carry `DEMO`.
  - **PIO₂ is not recomputed in the client:** the value from the `dashboard` is shown.
- [ ] **6.4 Dynamic charts (0.75 h)**
  - uPlot series from `readings` and live update with `telemetry.tick`.
  - Configurable window, drawn severity bands and threshold mark.
  - Charts readable in light and dark mode.
- [ ] **6.5 Human body (0.75 h)**
  - SVG silhouette with six indicators: head (mood and headache), lungs (SpO₂), heart, blood and organs (radiation), temperature and bones and muscle.
  - Each indicator uses the traffic light with a number and icon. On tapping: value, the NASA human research program hazard it relates to and evidence state.
  - Body values carry `DEMO` and "simulated".
- [ ] **6.6 Alert panel (1.25 h)**
  - **Actions first**, then the reason. Order: what to do, why (rule, measured value, document, requirement and state), probable cause (air or body), when to escalate.
  - **Acknowledge** button (`acknowledgeAlert`) with optimistic state and typed error handling.
  - It shows `recommendation.ready` first (template with citations) and then `recommendation.enriched` (model text) **without layout jumps**.
  - Critical alert: border, optional sound and vibration, and `aria-live`.
- [ ] **6.7 Empty and error states (0.75 h)**
  - No data: "Waiting for simulator readings" with a skeleton.
  - WebSocket down, GraphQL error, no recommendation yet and model absent.
  - Environment selector (ship, station, rover or base) and scenarios screen for the demo.

**Acceptance criteria**

- With the mocks, the high-CO₂ scenario turns the traffic light red, shows the alert with actions and source, and allows acknowledging it.
- Every state has shape, icon and text, not only color.
- The "not a medical device" banner is seen on every screen.
- Cutting and restoring the WebSocket resumes without losing or duplicating alerts.
- Accessibility Lighthouse of 90 or more and full keyboard navigation.

**Tests**

- Vitest + Testing Library: `SevPill`, `EvidenceBadge`, gauge with bands, `useWs` (resume and duplicates).
- Playwright against mocks: CO₂ scenario, acknowledge alert, WebSocket drop.

---

### F7 · Ship panel · 7 h · P0

**Objective:** show the ship plan with its zones, the incident tickets and the gas charts per zone, measured continuously.

**Depends on:** F0. **Mock:** same as F6, plus fixtures of `ship`, `incidents` and `incidentTypes`. At I3 (hour 16) it moves to the real thing.

**Contracts it consumes**

| Channel | Operation or message |
| --- | --- |
| GraphQL | `ship`, `incidents`, `incident`, `zoneReadings`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| WebSocket | `incident.opened · incident.updated · incident.resolved`, `zone.status`, `telemetry.tick` (per zone), `task.assigned` |
| REST | `POST /api/v1/sim/scenarios/{key}:start · :stop` with `zone_id` (demo mode) |

**Tasks**

- [ ] **7.1 SVG plan (1.5 h)**
  - It is drawn from `ship` using `zone.layout` (JSON: position and size). **No fixed coordinates in the code:** changing from a ship to a lunar base is changing data.
  - Each zone has a color per state (green, amber, red, magenta), a severity icon and a hatched stroke for critical.
  - Pin with the ticket identifier (`INC-0001`) and `+n` if there are more.
  - Selection by click and by keyboard. Quick CO₂ and O₂ reading inside each zone.
- [ ] **7.2 Real time (0.75 h)**
  - Subscription to `zone.status` and `incident.*`. It updates the plan and the list without reloading.
  - `telemetry.tick` per zone feeds the charts and the quick reading.
- [ ] **7.3 Charts per zone (1.5 h)**
  - Six metrics: O₂ (PIO₂), CO₂ (ppCO₂), N₂, humidity, temperature and pressure.
  - 90 s live window, with severity bands and the **ANOMALY** mark when the backend reports it. History with `zoneReadings`.
  - Current value with color, state icon and evidence label (the humidity and temperature bands are `DEMO`).
  - "Live" indicator and pause button.
- [ ] **7.4 Tickets (1.25 h)**
  - Card with identifier, severity, state, title, **location** (zone and deck), origin (automatic alert or manual report), **description**, history and tasks.
  - Actions: acknowledge and resolve. On automatic tickets, **resolve stays disabled while the values remain out of range**, with the explanation in view.
  - Notice "Normal values: it can be closed" when `alert_resolved` arrives.
  - Order by severity and age. Resolved ones are dimmed.
- [ ] **7.5 Report form (1 h)**
  - Category → type → default zone and severity, from `incidentTypes`. Optional title (if empty the type is used) and description.
  - It sends `reportIncident`. Typed `IncidentError` handling.
- [ ] **7.6 Type catalog (0.5 h)**
  - List of the 61 types in 12 categories, filterable. Each row shows detection (`AUTO` or `MANUAL`), severity, evidence and typical zones.
  - "Report" button that fills the form.
- [ ] **7.7 Demo mode (0.5 h)**
  - Buttons to provoke scenarios per zone (pressure leak, high CO₂, humidity, O₂ failure, heat) and "Normalize everything".
  - Only visible in development and jury profiles.

**Acceptance criteria**

- With the mocks, one scenario per zone paints the zone, opens a ticket with description, severity and location, and it appears in the list and as a pin on the plan.
- Selecting a zone or a ticket shows its charts.
- The plan is drawn only from data: changing the `zone.layout` JSON changes the plan.
- The interface works at 360 px wide: the plan scrolls inside its panel.
- The six graphic indicators have shape, icon and text.

**Tests**

- Vitest: plan render from data, ticket order and the "Resolve" button rule.
- Playwright against mocks: provoke scenario → ticket → acknowledge → normalize → resolve.
- Visual test of light and dark.

---

### F8 · Knowledge with demo data · 3 h · P0 · RAG

**Objective:** for each alert to have a deterministic recommendation with a citation, without depending on any model.

**Depends on:** F0. **Mock:** in-memory bus with sample `alert_raised` events and a fake `RuleQuery` facade.

**Contracts**

| Direction | Contract |
| --- | --- |
| Consumes | Event `monitoring.alert_raised` (payload: `alert_id`, `zone_id`, `rule_key`, `severity`, `evidence`, `cause_hint`). Monitoring's `RuleQuery` facade (rule and `action_key`) |
| Publishes | `knowledge.recommendation_ready` (`alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`) |
| Exposes | `KnowledgeQuery` and `ActionCatalogQuery` facades. GraphQL `knowledgeSearch(query, k)` |

**Tasks**

- [ ] **8.1 Hexagonal skeleton (0.5 h)**
  - Ports: `KnowledgeSource`, `TextComposer`, `ChunkRepository`. Adapters: `demo_source`, `template_composer`, `sql`.
  - `contracts.py` with `RecommendationReady` and `Citation`. Read-only `facade.py`.
- [ ] **8.2 Schema and migration (0.5 h)**
  - `knowledge` schema with `document`, `chunk`, `action`, `recommendation` and `recommendation_action` (see section 4.2). Own Alembic migration in `migrations/knowledge/`.
- [ ] **8.3 Demo adapter (0.75 h)**
  - Catalog of actions and recommendations per rule, in versioned JSON: `env-co2-1h`, `env-pio2`, `env-ptotal`, `env-dpdt`, `env-n2`, `env-rh`, `env-t` and the trend rule.
  - **Everything marked `DEMO` and labeled as fictitious**, with the sentence "demo data, not NASA data".
  - The actions match the incident type catalog (for example, `revisar_ventilacion_y_filtros` for CO₂).
- [ ] **8.4 `alert_raised` handler (0.75 h)**
  - Consumer `knowledge.on_alert_raised`, idempotent by `(consumer, event_id)`.
  - It builds the recommendation (actions, citations, evidence state) and publishes `recommendation_ready` in the same transaction.
  - **It waits for no model.**
- [ ] **8.5 Facades and GraphQL (0.5 h)**
  - `ActionCatalogQuery` (title and description of an action, used by Missions). `KnowledgeQuery` (text search over what is loaded).
  - `knowledgeSearch` resolvers registered in the schema A composes.

**Acceptance criteria**

- Given an `alert_raised` of `env-co2-1h`, a recommendation is generated with at least two actions and a citation with document, requirement and evidence state.
- Delivering the same event twice **does not duplicate** the recommendation.
- With the demo adapter, every answer carries the `DEMO` label.
- Without Ollama or network, everything works.
- `import-linter` green: `knowledge` imports nothing from another module except `contracts` and `facade`.

**Tests**

- Domain `pytest`: one recommendation for each rule of the catalog.
- Idempotency test with a duplicated event.
- Contract test: `RecommendationReady` validates against its Pydantic model.

**Milestone:** I4 (hour 17). The real event arrives from A and the recommendation appears in the alert panel.

---

### F12 · RAG over NASA PDFs · 4 h · P1 (fits before the delivery) · RAG

**Objective:** for the recommendations and answers to come from real fragments of the public documents, with a verifiable citation.

**Depends on:** F8.

**Input documents**

| Document | State | Use |
| --- | --- | --- |
| NASA-STD-3001 Vol. 1 Rev C | Read (sections 3 and 4) | Crew health, radiation, baseline-related criteria |
| NASA-STD-3001 Vol. 2 Rev F | Read (section 6 and part of 7.1) | Atmosphere, water, acoustics, vibration, radiation, nutrition |
| OCHMO-TB-002 (ECLSS) | Read | Summary of atmosphere, water and life support |
| OCHMO-TB-003 (habitable atmosphere) | Read | Hypoxia, hyperoxia, decompression |
| OCHMO-TB-004 (CO₂) | Read | Symptoms by CO₂ level, Apollo 13 case |
| OCHMO-TB-044 (medical operations) | Read | Role of the CMO, space motion sickness |
| Medical kit checklist | Read | Catalog of actions and on-board measurements |
| Human Integration Design Handbook, OCHMO-STD-100.1A, ISS Medical Emergency Manual | **Not opened** | Optional. The manual comes from a transparency release: **check the license and currency** |

**Tasks**

- [ ] **12.1 Selection and license (0.5 h)**
  - Manifest `data/knowledge/manifest.json` with code, title, URL, `license_status` and `verification_state` per document.
  - **No PDF is packaged without confirming its license.** The doubtful ones are indexed locally and documented.
- [ ] **12.2 Ingestion (1.25 h)**
  - Command `python -m spaceapp.knowledge.ingest`: extracts text per page, detects requirement references (`[V2 6004]`, `[V1 4033]`, `Table 6.2-1`) and fragments by requirement or section with a short overlap.
  - It stores per fragment: document, requirement number, page, content and `evidence_state`.
  - **Tables that come as an image** (Table 6.2-1 and figures): they are transcribed by hand or taken from the rule catalog, and marked as transcribed.
  - Idempotent ingestion: running it again does not duplicate fragments.
- [ ] **12.3 Search (0.75 h)**
  - First **full text** (`tsvector` in Spanish), which needs no model.
  - Optional vector with pgvector if there is a local embeddings model. **Which one is still to be decided** (section 11).
  - Minimum relevance threshold: below the threshold, there is no passage.
- [ ] **12.4 Answer policy (0.75 h)**
  - Answer **only** with retrieved passages, with mandatory citation (document, requirement, page and state).
  - Without a passage: "I don't have that information in the loaded sources". **A protocol is never invented.**
  - If the content comes from the demo adapter, the answer says "demo data, not NASA data".
  - Adapter switch by profile: `jurado` uses RAG and falls back to demo if a passage is missing.
- [ ] **12.5 Evaluation (0.5 h)**
  - Set of about 15 questions with the expected passage (CO₂ and headache, hypoxia, cabin pressure, space motion sickness, CMO role, medical kit, radiation limits, etc.).
  - Metrics: hit of the expected passage in the first 3 and **zero answers without a source**.
- [ ] **12.6 Passage finder in the SPA (0.25 h)**
  - Screen with search, list of passages with citation and state, and a link to the full fragment.

**Acceptance criteria**

- `knowledgeSearch("headache CO₂")` returns the TB-004 fragment with document and state.
- A question outside the sources returns "I don't have that information..." and no invented citation.
- The full ingestion is repeatable and runs without internet.
- The evaluation passes the agreed threshold and there are no answers without a source.

**Tests**

- Golden ingestion tests (a short sample PDF with expected fragments).
- Search tests with the evaluation set.
- Policy test: question without a passage → no-information message.

---

### F9 · Delivery for the jury (joint with A) · 1.5 h for B · P0

**Objective:** for the jury to run everything with one command, without internet.

**Depends on:** F5, F7 and F8 (hour 21).

**B's tasks**

- [ ] **9.1 SPA in the image (0.5 h):** build `web/` and serve it from the same container (or from a static server of the compose). Profile environment variable visible in the interface.
- [ ] **9.2 B's layer in Docker (0.5 h):** isolate Ollama and Whisper in their own layer or container of the compose, behind ports with a null adapter. Include the already indexed fragments and the small Whisper model. Document the final size.
- [ ] **9.3 Test on another computer (0.5 h, with A):** without internet, without GPU and with the microphone blocked. Text input must work.

**Acceptance criteria**

- A single command raises backend, database and SPA with the `jurado` profile.
- Without Ollama, the template recommendation with a citation keeps working.
- Without a microphone, the assistant works by text.

**Milestone:** I6 (hour 22.5).

---

### F13 · Assistant: text and Ollama · 3 h · P1 · RAG

**Objective:** for the astronaut to ask by text and receive an answer with a citation, in streaming.

**Depends on:** F8.

**Contracts**

| Direction | Contract |
| --- | --- |
| Exposes | GraphQL `askAssistant(text, conversationId)`, `confirmUtterance(id, text)`, `conversation(id)` |
| Publishes | `assistant.answer_ready` (`utterance_id`, `text`, `citations[]`) |
| WS messages | `assistant.transcript`, `assistant.token`, `assistant.answer` (emitted by A's gateway from the events) |
| Reads | `KnowledgeQuery` (its own) and Monitoring's `ActiveAlertsQuery` |

**Tasks**

- [ ] **13.1 Module and schema (0.5 h):** hexagonal skeleton of `assistant`, tables `conversation` and `utterance`, own migration.
- [ ] **13.2 GraphQL use cases (0.5 h):** `askAssistant`, `confirmUtterance` and `conversation`, with typed errors.
- [ ] **13.3 Answer flow (1 h)**
  - `KnowledgeQuery` → passages with citation → `TextComposer` (Ollama) that writes **only with what was retrieved**.
  - Time limit of **8 s**: if it expires, the answer is the passages as plain text.
  - Token streaming and final answer with citations.
  - Active alerts context: the answer may mention the current alert, **without changing or deciding it**.
- [ ] **13.4 `LlmGateway` port (0.5 h):** Ollama, n8n (optional) and null adapters. The null one returns the passages unwritten.
- [ ] **13.5 Assistant interface (0.5 h):** chat, example questions, citations with a link to the passage, mode chip ("local" or "cloud" depending on the adapter) and "I don't have that information..." state.

**Acceptance criteria**

- "Why do I have a headache?" with high CO₂ answers with the TB-004 passage and its citation.
- Without Ollama or after more than 8 s, the answer still arrives with the passages.
- A question without a passage does not produce an invented answer.
- The assistant never changes the state of an alert.

**Tests**

- `pytest` with a fake `LlmGateway`: timeout, null and streaming.
- Playwright: question with a passage and question without a passage.

---

### F14 · Voice with Whisper · 3 h · P1 · RAG

**Objective:** speak to the system without typing, with confirmation before acting.

**Depends on:** F13.

**Contracts:** REST `POST /api/v1/voice/utterances` (audio `webm` or `wav` and `conversation_id`; answers `202` with `utterance_id`). WebSocket `assistant.transcript`.

**Tasks**

- [ ] **14.1 `SpeechToText` port and local Whisper (1 h):** `faster-whisper` with a small model that runs without GPU. Null adapter for text.
- [ ] **14.2 Audio route (0.75 h):** store the audio, answer `202` at once, transcribe asynchronously and publish the transcript so it arrives over WS.
- [ ] **14.3 Voice interface (0.75 h):** hold-to-talk button (`MediaRecorder`), **editable** transcript, confirm button and "listening" state.
- [ ] **14.4 Tests with noise and medical terms (0.5 h):** sample audio, words such as "hypoxia", "ppCO₂", "partial pressure". Text input always available.

**Acceptance criteria**

- Speaking produces an editable transcript. **Nothing is acted on without confirming.**
- Without Whisper or without a microphone, the system keeps working by text.
- An emergency does not depend on voice.

**Technical note:** the browser only allows the microphone on `localhost` or over HTTPS. Document it in the README.

---

### F10 · Tasks, interface part · 1.5 h · P1

**Objective:** for the crew to see their tasks of the day, create their own and block the ones from Earth with a reason.

**Depends on:** F9. **Mock:** the tasks schema is already frozen. B builds the interface on mocks until A finishes the backend (A's F10).

**Contracts it consumes:** `tasks(kind, status)`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask(effective)`, `snoozeReminder`, `setConsent`. WS `task.assigned · reminder.due` and `plan.received · plan.applied`.

**Tasks**

- [ ] **10.1 Task list (0.5 h):** filters All, Health, Ship and Incidents, grouped, with an **origin label** (Earth, System or Crew) on each card.
- [ ] **10.2 New own task (0.5 h):** form of type, zone and title. Edit and delete only those with origin `TRIPULACION`.
- [ ] **10.3 Block and effectiveness (0.25 h):** "I cannot do it" with a reason (it is not deleted), "Did it work?" when completing and snoozing the reminder.
- [ ] **10.4 Streak, achievements and consent (0.25 h):** only health routines add to the streak. **Critical alerts are not gamified.** Switch for the "tasks" category in "Link and privacy".

**Acceptance criteria**

- A task from Earth cannot be edited or deleted, only completed, snoozed or blocked with a reason.
- An own task can be created without a link.
- Alert measures, those from Earth and incidents add no points.

---

### F11 · Control center panel, interface part · 2 h · P1

**Objective:** for the control center to schedule tasks with option B: versioned plans with a local copy on the ship.

**Depends on:** F9. A finishes the backend earlier (A's F11).

**Contracts it consumes (role `ground`):** `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan`, `PUT /api/v1/groundlink/link` (link control in the demo) and the messages `plan.received · plan.applied`.

**Tasks**

- [ ] **11.1 `/ground` route and design (0.5 h):** the same SPA with role `ground`. Make clear on the screen that it is the Earth panel.
- [ ] **11.2 Draft and publish (0.75 h):** active templates with their state on the ship (pending, received, applied, completed, blocked with a reason), draft of the next version, add template, mark to cancel and **Publish plan vN**.
- [ ] **11.3 Plan state and link (0.5 h):** pipeline "Published → On the link → Received → Applied → Confirmed" and link control with a delay for the demo.
- [ ] **11.4 Notice on the ship (0.25 h):** "Plan vN applied" on receiving `plan.applied`.

**Acceptance criteria**

- With the link cut, the plan stays "queued". When restored it arrives, is applied and confirmed.
- A repeated version is ignored, a corrupt plan is rejected as a whole and an invalid item is rejected alone.
- The state of tasks is only seen if the crew shares the "tasks" category.

**Milestone:** I7 (hour 32).

---

### F16 · Alexa as a fallback · 2 h · P2 · RAG

**Objective:** have a fallback voice adapter for the demo, **only if Whisper gets stuck**.

**Depends on:** F14.

**Tasks**

- [ ] **16.1 Development skill (0.75 h):** interaction model and the team's developer account. A skill in development mode runs only in that account, and is enough for the demo.
- [ ] **16.2 Webhook (0.5 h):** `POST /api/v1/alexa/webhook` active **only with the `dev2` profile**. It translates the intent into `askAssistant`.
- [ ] **16.3 Public tunnel (0.5 h):** endpoint reachable by Alexa.
- [ ] **16.4 Documentation (0.25 h):** the interface shows "Voice in the cloud: not autonomous". It is said so in the presentation.

---

## 4. Design of B's modules

### 4.1 B's public contracts

**Events B publishes** (all through the outbox):

| Event | Receivers | Payload |
| --- | --- | --- |
| `knowledge.recommendation_ready` | Missions (A), Gateway (A), Earth link (A) | `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]` |
| `knowledge.recommendation_enriched` | Gateway (A) | `recommendation_id`, `text` |
| `assistant.answer_ready` | Gateway (A) | `utterance_id`, `text`, `citations[]` |

**Event B consumes:** `monitoring.alert_raised` (from A).

**Read facades**

| Facade | Who uses it | What for |
| --- | --- | --- |
| `ActionCatalogQuery` (B) | Missions (A) | Title and description of an action |
| `KnowledgeQuery` (B) | Assistant (B) | Citable passages |
| `RuleQuery` (A) | Knowledge (B) | Rule and `action_key` of an alert |
| `ActiveAlertsQuery` (A) | Assistant (B) | Active alerts context |

**Shape of a citation (`Citation`)**

```graphql
type Citation {
  documentCode: String!
  requirementRef: String
  page: Int
  excerpt: String!
  evidenceState: EvidenceState!   # VERIFICADO | TB | DEMO | NO_VERIFICADO
}
type Recommendation {
  actions: [Action!]!
  body: String!
  citations: [Citation!]!
  composedBy: String!             # plantilla | llm  (template | llm)
}
```

### 4.2 Data schemas

**`knowledge` schema**

| Table | Main columns |
| --- | --- |
| `document` | `id`, `code` (unique), `title`, `url`, `license_status`, `verification_state`, `ingested_at` |
| `chunk` | `id`, `document_id` (FK), `requirement_ref`, `page`, `content`, `embedding` (optional), `evidence_state` |
| `action` | `id`, `key` (unique), `title`, `description`, `category`, `source_chunk_id` (FK, optional) |
| `recommendation` | `id`, `alert_id` (soft reference to Monitoring), `source_kind` (`DEMO` or `RAG`), `body`, `citations` (jsonb), `composed_by`, `created_at` |
| `recommendation_action` | `recommendation_id` (FK), `action_id` (FK) |

**`assistant` schema**

| Table | Main columns |
| --- | --- |
| `conversation` | `id`, `crew_member_id` (soft reference), `channel` (voice or text), `created_at` |
| `utterance` | `id`, `conversation_id` (FK), `role` (crew or assistant), `text`, `adapter` (whisper, alexa or text), `confirmed`, `citations` (jsonb), `created_at` |

Rules: no foreign keys to other modules. `chunk.embedding` is optional: without it, search is full text.

### 4.3 Recommendation flow per alert

1. `monitoring.alert_raised` arrives at Knowledge's handler (idempotent).
2. `RuleQuery` is queried to obtain the rule and its `action_key`.
3. The passage or the action is looked up in the active source (`demo` or `rag`) and the **template recommendation with a citation** is built.
4. It is stored and `recommendation_ready` is published in the same transaction.
5. **Optional:** `TextComposer` (Ollama) writes an explanation with an 8 s time limit and publishes `recommendation_enriched`. If it fails or expires, nothing happens: the template is already on screen.

### 4.4 Which adapter each profile activates

| Port | `dev1` | `dev2` | `jurado` |
| --- | --- | --- | --- |
| Input voice | Local Whisper | Alexa (cloud, demo only) | Local Whisper |
| Knowledge | Demo + RAG | Demo + RAG | RAG. Falls back to demo if a passage is missing |
| Wording | Ollama | Ollama | Ollama. Falls back to the template if it takes more than 8 s |

The variable name (`SPACEAPP_PROFILE`) and the default value `jurado` are a **proposal** and not a decision taken.

---

## 5. Contracts B consumes from A

### 5.1 GraphQL

| Screen | Operations |
| --- | --- |
| Cabin | `dashboard`, `readings`, `alerts`, `alert`, `rules`, `crewMember`, `acknowledgeAlert`, `recordBaseline`, `setConsent` |
| Ship | `ship`, `incidents`, `incident`, `zoneReadings`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| Tasks | `tasks`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask`, `snoozeReminder` |
| Link | `groundLinkStatus`, `syncGroundLinkNow`, `setConsent` |
| Earth panel (role `ground`) | `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |

### 5.2 WebSocket (`/ws`)

Server message: `{ "seq": 18342, "topic": "alerts", "type": "alert.raised", "at": "…", "data": { … } }`. `seq` is the outbox `id` when the message comes from an event. On ticks it is `null`.

| Message | Used in |
| --- | --- |
| `telemetry.tick` | Cabin and ship |
| `alert.raised · updated · resolved` | Cabin |
| `recommendation.ready · enriched` | Alert panel |
| `incident.opened · updated · resolved`, `zone.status` | Ship |
| `task.assigned · reminder.due` | Tasks |
| `plan.received · applied` | Tasks and Earth panel |
| `assistant.transcript · token · answer` | Assistant |
| `groundlink.state` | Link |
| `scenario.changed` | Demo mode |
| `subscribe · unsubscribe · resume · ping` | Data layer |

**Backpressure:** queue of 500 messages per client. `telemetry.tick` are dropped first. **Alerts are not dropped.**

### 5.3 REST

| Route | Use |
| --- | --- |
| `POST /api/v1/sim/scenarios/{key}:start · :stop` | Demo mode |
| `PUT /api/v1/groundlink/link` | Cut or restore the link in the demo |
| `GET /api/v1/rules/catalog.json` | Export the rule catalog |

---

## 6. Quality and tests

| Level | What it covers | Tool |
| --- | --- | --- |
| Components | `SevPill`, `EvidenceBadge`, gauge, ticket card, report form | Vitest + Testing Library |
| Data layer | `useWs`: resume, duplicates, order, dropping ticks without dropping alerts | Vitest |
| End to end with mocks | Scenario → alert → acknowledge. Scenario per zone → ticket → resolve | Playwright |
| Contract | Types generated from the schema. B's events against their Pydantic models | `graphql-codegen` in CI, `pytest` |
| Knowledge | One recommendation per rule, idempotency, policy without a passage | `pytest` |
| Ingestion and search | Golden tests, evaluation set and zero answers without a source | `pytest` |
| Assistant | 8 s time limit, null, streaming | `pytest` with a fake `LlmGateway` |
| Accessibility | AA, keyboard, `aria-live` on alerts, not depending on color | Lighthouse, axe |
| Offline | Container without network: the whole flow with the `jurado` profile | Manual, on another computer |

---

## 7. Definition of done

A phase of B is **done** when:

- [ ] It meets its acceptance criteria.
- [ ] B's CI is green (`eslint`, `tsc`, `vitest`, `ruff`, `mypy`, `import-linter`, `pytest`).
- [ ] There are no values without an evidence label (`VERIFICADO`, `TB`, `DEMO` or `SIMULADO`).
- [ ] The state of every alert or severity has shape, icon and text.
- [ ] It works without internet and without Ollama (null adapter).
- [ ] There is a short note in the README of the module or the feature.
- [ ] If it touches a contract, the other developer reviewed it.

---

## 8. Specific risks of B

| Risk | Probability | Mitigation |
| --- | --- | --- |
| A's API is late and B gets blocked | High | Schema frozen at I0, generated mocks and WS recordings. B does not depend on A until I2 |
| A contract change breaks the interface without notice | Medium | Types generated in CI: the build fails at once |
| Poor-quality text extraction from the PDFs or tables as an image | High | Manual transcription of key tables, golden tests and evaluation |
| Slow Ollama without a GPU on the jury's machine | High | The template recommendation with a citation comes out first. Optional wording with an 8 s limit |
| Whisper heavy or with poor accuracy on medical terms | Medium | Small model, mandatory confirmation and text input always available |
| The microphone fails in Docker or outside `localhost` | Medium | Document HTTPS or `localhost`. Text as a working alternative |
| License of the PDFs for the Docker image | Medium | `license_status` per document and do not package the doubtful |
| Too many live charts or SVG at 1 Hz slow down the interface | Low | uPlot, tick coalescing and redrawing only the selected zone |
| WebSocket reconnections generate duplicates or losses | Medium | `seq` per message, deduplication and `resume` from the last id |
| If B is missing, A does not know their part | Medium | Short README per module and contract tests as documentation |

---

## 9. Coordination with Dev A

**What B asks A for**

1. At I0: in-memory bus, base repository and frozen contracts.
2. At I1: the real outbox.
3. At I2 to I5: the real readings, incidents and gateway, to remove the mocks.
4. Event `alert_raised` with `zone_id` and the `RuleQuery` facade.

**What B delivers to A**

1. `recommendation_ready` and the `ActionCatalogQuery` facade (Missions uses them).
2. `assistant.answer_ready` so the gateway turns it into WS messages.
3. The Knowledge and Assistant resolvers to compose the schema.

**When to warn**

- If a contract needs a new field: **before** implementing it, with a request to the owner.
- If a mock does not reflect real behavior: when detected, not at the milestone.
- At the end of each phase: one line with what is ready and what is missing.

---

## 10. Pending decisions that affect B

They are not decided without consulting. Meanwhile the stated assumption is used.

| # | Decision | Current assumption |
| --- | --- | --- |
| 1 | Does the RAG only return passages with a citation or does it also write with Ollama? | It writes with Ollama, falling back to the template with an 8 s limit |
| 2 | Does n8n stay as orchestrator or is Ollama called directly? | n8n stays as an optional adapter. By default Ollama is called directly (replaced on 15 Nov 2026: n8n is mandatory for the assistant, see logbook E18) |
| 3 | Is F12 (full RAG) raised to P0? | It stays in P1, although it fits before the delivery |
| 4 | Local embeddings model | None at first: full text. Vector if a model is decided (decided on 15 Nov 2026: `bge-m3`, logbook E23) |
| 5 | Name of the profile variable and default value | `SPACEAPP_PROFILE`, with `jurado` by default |
| 6 | Interface language for the jury | Spanish. Pending whether an English version is needed (decided on 15 Nov 2026: English, logbook E21 and E33) |
| 7 | Authentication of the Earth panel | Role `ground` by local selection, without external accounts |
| 8 | Which extra documents are indexed (HIDH, OCHMO-STD-100.1A, ISS manual) | Only the seven read. The others, optional and with a license to review |
| 9 | Demo scenario (transit to Mars, lunar base or ISS) | Transit ship. Changing is changing data |

---

## 11. Dev B master checklist

**P0 cut (18.5 h)**

- [ ] F0 · `web/` project, codegen, mocks and reviewed contracts (I0)
- [ ] F6 · Cabin panel, charts, human body and alert panel
- [ ] F7 · Plan, tickets, per-zone charts, form and incident catalog
- [ ] F8 · Knowledge with demo data and `alert_raised` handler (I4)
- [ ] F9 · SPA in the image, B's layer in Docker and offline test (I6)

**P1 and P2 (15.5 h)**

- [ ] F12 · RAG over NASA PDFs: ingestion, search, policy and evaluation
- [ ] F13 · Text assistant with Ollama
- [ ] F14 · Voice with Whisper and confirmation
- [ ] F10 · Tasks: list, new task, block with a reason and consent
- [ ] F11 · Control center panel (I7)
- [ ] F16 · Alexa as a fallback (only if Whisper gets stuck)

**Closing**

- [ ] README of `web/`, `knowledge` and `assistant`
- [ ] Demo script with the scenarios and the order of the screens
- [ ] Final test on another computer, without internet, with the `jurado` profile
