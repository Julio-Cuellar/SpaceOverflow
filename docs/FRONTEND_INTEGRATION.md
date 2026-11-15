# SYRA frontend: architecture review and Dev A integration

## Delivered application

The active application is a React 18 / Vite 8 / TypeScript SPA. `web/src/main.tsx` mounts `Root`, which now renders `console/ConsoleApp`. It replaces the old interface at the application entry point. The HTML mockups remain reference artifacts and are not the production app. Headings use bundled Montserrat and body text uses bundled Roboto; the application needs no Google Fonts connection. The cyan atmosphere (#65B5CB), blue navigation, sharp cards, portrait cards and per-person body indicators follow the approved mockups.

All new UI labels, validation messages, accessibility text, fixtures, documentation and frontend-owned error messages are English. Spanish enum values remain unchanged on the wire. Backend-authored task titles, descriptions, zone names and source quotations are content: Dev A must return English content for an entirely English deployment. Source quotations are not silently rewritten.

| Route | Audience | Function |
| --- | --- | --- |
| `/` | Mission control | Crew preview cards, global habitat readings, cited active alerts, recent incidents |
| `/crew` | Authorized mission control | Individual profile selection; live wearable profiles remain unavailable until the crew service exists |
| `/habitat` | Habitat operations | Data-driven selectable layout, zone history and rule thresholds, ticket lifecycle, incident catalog, simulator |
| `/tasks` | Crew operations | Categories and status filters, create/edit/delete own tasks, completion effectiveness, blockers, snooze, applied plan and health progress |
| `/assistant` | Mission support | Text questions, retrieved citations, voice review and confirmation, optional read-aloud |
| `/ground` | Ground operations | Template drafts, edits, cancellation, publication, delivery stages, link controls and sync |
| `/settings` | Current session | Backend health, provenance, rule catalog access, profile/consent integration boundaries |
| `/dashboard-tripulation` | Signed-in astronaut | Own health, tasks and tickets; assigned zone telemetry and shared incidents; own routine; floating assistant |

The personal route is not present in the control-center sidebar. Its local My day / My habitat / My routine controls stay within the personal workspace. The assistant opens from a round button in the lower right, traps focus with a native dialog, supports Escape, and retains the conversation when closed. Changing data source or personal identity resets the assistant context.

## Findings from the repository review

The architecture describes a modular Python monolith with hexagonal modules, transaction/outbox events, GraphQL commands and queries, and WebSocket push. Frontend changes preserve that separation. The browser never evaluates alert rules, derives PIO₂, decides thresholds or uses the assistant to mutate alerts.

Repository files were checked against `docs/architecture-plan.md`, `docs/tasks-dev-a.md`, `docs/tasks-dev-b.md`, the current logbook, the V2 specification, Python composition roots and inbound adapters, and the existing web data, feature and test layers.

| Area | State in this checkout | Frontend treatment |
| --- | --- | --- |
| Platform/outbox, monitoring, telemetry | Implemented in the main Python app; F0–F3 recorded complete | Consume health, rules and scenario REST routes; preserve their contracts |
| Facility/incidents | Contracts/facades exist; full inbound/API implementation absent | Gateway and complete incident UX prepared against the V2 target |
| GraphQL and WebSocket | Main app has no `/graphql` or `/ws` gateway; exported schema and WS schema absent | urql POST queries/mutations; pagination; reconnect/resume; contract gate after merge |
| Engagement/tasks | Public contracts exist; production task endpoints absent | Task operations and source restrictions isolated behind the gateway |
| Ground link/plans | Public contracts exist; production control endpoints absent | Draft/publication/link UX; deterministic demonstration adapter |
| Crew/session/consent | No authenticated crew read model or scoped ownership implementation | Personal backend mode fails closed. Proposed session read model described below |
| Knowledge and assistant | Implemented modules, n8n/Ollama integration and local development server | Existing `/dev/ask` consumed, with citations and explicit errors |
| Voice | Whisper transcription and Kokoro routes in the assistant development server | Upload → poll → editable transcript → confirm/discard; optional WAV playback |
| Old frontend | Spanish demo state and fixtures; most mission features not connected | Retained as unmounted legacy code/tests. New entry uses `src/console/` |

The V2 document describes backend work that is not present in this checkout. It names `contracts/schema.generated.graphql`, `contracts/openapi.json`, and `contracts/ws-messages.schema.json`; none is present here. `contracts/schema.graphql` is only the original minimal draft. It must not be mistaken for the final backend export.

## Data boundary

`Gateway` in `web/src/console/model.ts` defines reads, commands, zone history and realtime invalidation. Components receive `Mission` state and call `run(command)`; they do not know endpoint URLs or maintain a second authoritative copy of backend state.

- `console/data/demo.ts`: explicitly labeled, in-memory demonstration adapter. It implements ownership restrictions, blockers, effectiveness, ticket guards and queued plan delivery. Changes last until reload or adapter replacement. It does not impersonate a backend.
- `console/data/backend.ts`: urql with POST and same-origin credentials. No silent fallback to demo. Expected mutation-union errors map to English; uncertain network outcomes are reported as unconfirmed and re-read before retry.
- `console/data/useMission.ts`: scopes reads by route, refreshes after confirmed writes and realtime events, polls every ten seconds, and cancels obsolete reads. Data is tagged with its adapter and scope so a source/role switch cannot render the previous source's snapshot.
- `console/data/operations.ts`: V2 query and mutation documents. All pages of alerts/incidents are loaded using cursors, with repeated-cursor detection. No fabricated client IDs are sent in backend mode.

Rule catalogs are consumed from the implemented REST route. Raw telemetry ticks invalidate the view and refresh historical data; they do not rebuild dashboard severity or PIO₂ in the browser. Fixed threshold lines are drawn only for backend catalog rules of kind `umbral`, with a matching metric, source label, operator and window. Trend rules are not represented as fixed thresholds.

Realtime connects to `/ws`, resumes with `after_outbox_id`, deduplicates sequences and coalesces ticks through the existing stream queue. Reconnect uses bounded exponential delay. System messages do not advance the event cursor. Polling provides a read recovery path while the realtime gateway is absent. Local backend connectivity and the Earth link are displayed as separate concepts.

## Dev A implementation handoff

`contracts/frontend-integration.graphql` is a complete **integration target**, based on V2. Crew command payloads and full template zone/recurrence fields are explicit extensions to be implemented or reconciled by Dev A. It is not an exported or approved backend contract. `operations.ts` contains the exact requested fields and variables. After merge, the generated backend schema automatically replaces the target for code generation and validation.

| Dev A phase | Required functions | Frontend consumer and rules |
| --- | --- | --- |
| F2/F3, available | `GET /health`; `GET /api/v1/rules/catalog.json`; `POST /api/v1/sim/scenarios/{key}:start` / `:stop` | System status, catalog/thresholds and simulation. Scenarios send `zone.code`, never a fixture ID. Body includes `zone` and `speed` |
| F4 | `ship`, `incidents`, `incident`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` | Data-driven layout; ticket codes from the server. Manual reports use the catalog default severity. Automatic incidents remain open until explicitly resolved; reject `ACTIVE_ALERTS` |
| F5 | `dashboard`, paginated `alerts`, `alert`, `zoneReadings`; `acknowledgeAlert`; `/ws` | Typed response shapes in the target. Acknowledgement is idempotent. Dashboard values and derived metrics remain server-owned |
| F10 | `tasks`, `streak`, `groundPlan`; `createTask`, `updateTask`, `deleteTask`, `completeTask`, `snoozeTask`, `blockTask` | Preserve system/ground/crew origins. Edit/delete only `TRIPULACION`. Require blocker reason; snooze 1–1440 minutes. Incident tasks complete through incident resolution |
| F11 | `groundControl`; `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan`, `setGroundLink` | Return full view or `GroundError`. Monotonic versions, one in-flight plan, idempotent application, preserve completed crew work and cancellation semantics |
| F15 | `syncGroundLinkNow`, crew baseline and consent endpoints | Filter task sharing and blocked reasons on the server. Consent and baseline documents are part of the integration target; controls require a current authenticated session |
| Session extension | Authenticated current-user read model and resource authorization | Required for the personal route; see next section |

Events consumed: `telemetry.tick`, `alert.*`, `recommendation.*`, `incident.*`, `zone.status`, `task.*`, `groundplan.*`, and `groundlink.state`. Existing V2 message envelopes are accepted; the UI re-queries authoritative data instead of interpreting state transitions from arbitrary event text.

### Authorized crew directory extension

Mission Control can consume an authorized crew directory via `VITE_CREW_DIRECTORY_URL`, returning `{ crew: CrewMember[] }`. This optional read model populates the portrait cards and individual control-center profile view. Its members use the same profile shape as the proposed session schema. Require a mission-control role on the server. The personal route never loads this directory. No current backend roster route is assumed or invented when the variable is empty.

### Session extension: required for personal isolation

V2 has no authenticated current-user endpoint. Set `VITE_SESSION_URL` only after Dev A implements a trusted same-origin session read model. This is a proposed extension, not a currently working API route.

Expected response type is `Session` in `model.ts`:

```ts
{
  crewMember: { id, name, role, portrait, state, vitals, bloodPressure? },
  zoneId,
  tasks,          // only assigned to this authenticated person
  incidents,      // only reported by or assigned to this person
  sharedTasks,
  baselines?
}
```

Each personal measurement retains evidence and origin. Blood pressure is separate from environmental pressure. `portrait` selects one of the bundled illustrative assets in this prototype; real profile media needs its own approved media contract. This response is not stored in localStorage.

Required server behaviors:

1. Resolve identity from authentication, never a query-string user ID or the demo identity.
2. Return 401 without a session, and 403 when resource ownership/role is insufficient.
3. Filter private task and ticket reads as well as mutations. Checking only the UI is insufficient.
4. Authorize Ground operations independently of route visibility. Hiding a link does not enforce a role.
5. Authorize the current zone's shared incidents and sensor history.
6. Bind assistant retrieval and conversation access to the same authenticated scope before including private health context. The current `/dev/ask` sends question text only; the interface does not claim to provide server-side personalization.

Until this exists, backend personal mode displays a session-unavailable state and **does not reuse global tasks or another astronaut's health profile**. Demo mode contains one explicitly fictional personal session.

## Existing service configuration

The assistant development server and main API can run on different ports:

```bash
# Existing main API: rules and health work without the GraphQL merge.
.venv/bin/python -m uvicorn spaceapp.main:create_app --factory --host 127.0.0.1 --port 8002

# Existing assistant development server, usually already on port 8000.
.venv/bin/python -m spaceapp.devtools.assistant_server

# Vite proxies to each service without browser CORS changes.
cd web
SPACEAPP_API_PROXY=http://127.0.0.1:8002 \
SPACEAPP_ASSISTANT_PROXY=http://127.0.0.1:8000 npm run dev
```

After Dev A composes all services on one port, both proxy targets can point to that port. Proxy targets are server configuration, not exposed credentials. Public frontend configuration is documented in `web/.env.example`. Missing service routes show errors; configure `VITE_DATA_MODE=backend` to use backend mission data by default. With `demo`, the assistant still uses its real configured endpoint, and its adapter is labeled separately.

The production Vite bundle has no development proxy. `docker/frontend.Dockerfile`, `docker/frontend.conf.template` and `docker/compose.frontend.yaml` supply a static SPA server with API and WebSocket forwarding. Production history fallback must serve `index.html` for `/dashboard-tripulation` and the other SPA routes.

## Merge checks

```bash
cd web
npm ci
npm run codegen
npm run typecheck
npm run lint
npm test
npm run build

# Required before claiming real Dev A integration is complete:
# regenerate contracts/schema.generated.graphql from Dev A's merged backend first
npm run contracts:merge-check
```

`contracts:check` validates all 25 query/mutation documents against the exported schema when present, otherwise the integration target. `contracts:merge-check` additionally **fails if the backend export is absent**. Codegen uses the same preference and generates the combined contract types into the existing ignored output directory. `prebuild` runs codegen so a clean checkout does not depend on previously generated files.

A successful target-contract test establishes frontend consistency, not a working backend. A final end-to-end merge check must cover real sensor data → alert → cited recommendation → acknowledgement; zone event → incident → task → normalized values → explicit resolution; and ground publish → link interruption → restore → applied/confirmed.

## Verification and limitations

Frontend behavioral tests cover task ownership, blockers, progress synchronization, plan queuing, incident resolution guards, pagination, typed errors, REST response validation, realtime deduplication/resume, personal isolation and assistant conversation retention. Existing legacy tests remain regression evidence for older pure state logic, not proof of backend integration.

The current local verification result is:

- `304` Vitest tests passed across `45` files.
- Coverage: `90.28%` statements, `83.10%` branches, `89.45%` functions, `92.24%` lines.
- `npm run typecheck`, `npm run lint` and `npm run build` pass.
- `npm run contracts:check` passes all `25` GraphQL query/mutation documents against the integration target.
- `npm run contracts:merge-check` intentionally fails until Dev A exports `contracts/schema.generated.graphql`; this is the merge guard, not an application failure.
- `docker compose -f docker/compose.frontend.yaml config --quiet` passes.
- Browser review covered mission control and `/dashboard-tripulation` at desktop, tablet and mobile breakpoints. Review captures are stored in [`docs/assets/mission-overview-review.png`](assets/mission-overview-review.png) and [`docs/assets/personal-dashboard-review.png`](assets/personal-dashboard-review.png).

Real database/outbox workflows, real authentication, permission enforcement, full offline Docker delivery and Dev A's final GraphQL schema remain backend/integration acceptance work. Microphone capture requires localhost or HTTPS; transcription remains editable and no voice question is sent until confirmed. Read-aloud depends on the existing voice service and browser playback permission.

Technical implementation references: [Vite proxy configuration](https://vite.dev/config/server-options#server-proxy) and [React external-state integration](https://react.dev/reference/react/useSyncExternalStore).
