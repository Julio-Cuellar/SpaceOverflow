# Front-end specification

> Health monitor for astronauts · NASA Space Apps 2026
> Which screens the interface has, what data each one consumes and what it shows.
> Written by Dev A (backend) so that Dev B (interface) can connect the front end to the real backend.
> Source of truth for the contracts: `contracts/schema.generated.graphql`, `contracts/openapi.json` and `contracts/ws-messages.schema.json` (regenerated with `uv run python -m spaceapp.interfaces.contracts_export`). If this document and the contracts disagree, the contracts win.
> Status as of November 15, 2026 (version 2: the backend now returns the ticket code and the rule thresholds). What the backend **does not have yet** is in section 9.

## 1. Rules that apply to all screens

| Rule | What it means on screen |
| --- | --- |
| **Fixed notice** | Always visible: "Decision-support prototype. Not a medical device." and "Simulated data" (`Banner` component). |
| **Data origin** | Every `Vital` carries `origin` (`REAL`, `SIMULATED`, `REPLAY`). Today everything is `SIMULATED`: it is labeled as simulated. |
| **Evidence state** | Every datum with a standard carries `evidenceState`: `VERIFIED` (comes from NASA-STD-3001), `TB` (to be confirmed), `DEMO` (for demonstration), `UNVERIFIED`. It is shown with `EvidenceBadge`. A `DEMO` datum is never presented as if it were from NASA. |
| **Status light** | `Severity`: `NORMAL`, `ATTENTION`, `ALERT`, `CRITICAL`, in that order of severity. It is shown with `SevPill`, always with text and not only with color. |
| **Citations** | Every recommendation or assistant answer carries at least one citation (`documentCode`, `requirementRef`, `excerpt`, `evidenceState`). Without a citation, the assistant says "I don't have that information in the loaded sources". |
| **Critical alerts** | The response to an alert is not gamified: its actions do not count toward the streak. |
| **Expected errors** | They are not exceptions: mutations return a `union` (`...Payload` or `...Error` with `code` and `message`). The front end asks for `__typename` and shows `message`. |
| **Dates** | `DateTime` in ISO 8601 with time zone (UTC). `Date` is `YYYY-MM-DD`. Task times are ship time (UTC). |
| **Language** | Interface texts and backend messages in English. |

## 2. How it connects

| Channel | Path | What for |
| --- | --- | --- |
| GraphQL | `POST /graphql` | All reads and all user actions. |
| WebSocket | `/ws` | Server push only (alerts, readings, tickets, tasks, plan). Actions do **not** go through here. |
| REST | `/health`, `/api/v1/sim/scenarios/{key}:{start\|stop}` | Runtime profile and demo mode. |

**Development:** today the Vite server only redirects `/dev` to port 8000 and the backend has no CORS. A proxy must be added for `/graphql`, `/api` and `/ws` (the latter with `ws: true`), or CORS must be enabled.

**Habitat:** the only habitat in the demo is `transit-ship`. Any operation that asks for `habitatId` accepts that code or its UUID.

**Identifiers:** all `id`s are UUIDs as text. The backend's zone ids are **not** `z-lab` or `z-bridge` (those belong to the mocks): they are taken from `ship.zones[].id`.

**Profile:** `GET /health` returns `{"status": "ok", "profile": "jury" | "dev1" | "dev2"}`. Demo mode (scenarios, section 4.2) is visible in all three profiles, because the jury has to be able to trigger them. What changes with the profile is the backend side: the operations routes (requeue events and `outboxStats`) only exist in `dev1` and `dev2`.

**Types:** generate the TypeScript types from `contracts/schema.generated.graphql` and the message types from `contracts/ws-messages.schema.json`. `contracts/schema.graphql` is Dev B's draft and is no longer used as a source.

## 3. Screen map

| # | Screen | Route / tab | Who uses it | Main data |
| --- | --- | --- | --- | --- |
| 1 | **Cabin** | "Cabin" tab | Crew | Cabin vital signs, active alert with its recommendation, human body |
| 2 | **Facility** | "Facility" tab | Crew | Zone floor plan, per-zone charts, tickets, incident catalog, report |
| 3 | **Tasks** | "Tasks" tab | Crew | Tasks of the day, streak, own tasks, consent |
| 4 | **Assistant** | "Assistant" tab | Crew | Questions by text or voice with a cited answer |
| 5 | **Ground panel** | `/ground` | Mission control (role `ground`) | Templates, draft, publication and ground link |
| — | **Plan notice** | top strip | Crew | "Plan vN applied" |
| — | **Banner** | top strip | Everyone | Prototype and simulated-data notice |

## 4. Screens

### 4.1 Cabin

**What it shows**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Global status light | `globalSeverity` | `dashboard(habitatId: "transit-ship")` |
| Six vital signs | `vitals[]`: `key`, `label`, `value`, `unit`, `severity`, `evidenceState`, `origin`, `zoneId` | `dashboard` |
| Alert panel (just below the status light) | Most severe active alert: `ruleKey`, `severity`, `causeHint`, `evidence`, `raisedAt`, `zoneId` | `alerts(first: 20, status: RAISED)` and `alert(id)` |
| Alert rule | `rule`: `sourceRequirement`, `sourceDocument`, `evidenceState`, `parameter` | `alert(id) { rule }` |
| Recommendation | `recommendation`: `body`, `actions[]` (`key`, `title`, `description`), `citations[]`, `sourceKind` | `alert(id) { recommendation }` |
| Human body (6 indicators) | Head, lungs, heart, blood and organs, temperature, bones and muscle | **No backend yet** (section 9). The mock is kept and labeled `DEMO`. |

**The six vital signs** (`vitals[].key`): `pressure_kpa` (total pressure, kPa), `o2_pct` (oxygen, %), `co2_mmhg` (CO₂, mmHg), `temperature_c` (temperature, °C), `humidity_pct` (relative humidity, %) and `pio2` (inspired oxygen, mmHg, computed from the pressure and the oxygen). All with `domain: "cabin"`.

**How each one is computed** (to avoid surprises):
- Without alerts, the value is the average of the zones and `zoneId` is `null`.
- With alerts, the sign takes the severity, the zone, the value and the evidence of its most severe alert. This way the CO₂ card can say "ALERT in the laboratory".
- `globalSeverity` is the worst of all active alerts, even those that have no sign of their own (for example, nitrogen).
- If there are no readings yet, `vitals` comes back empty: show "No data yet".

**Action:** "Acknowledge" button → `acknowledgeAlert(id, note)`. Result `AlertAcknowledgedPayload { alert, alreadyAcknowledged }` or `AlertError { code: NOT_FOUND | ALREADY_RESOLVED, message }`. It is idempotent: acknowledging twice gives no error, it returns `alreadyAcknowledged: true`.

**Active alerts:** there is no "active" filter. `RAISED` and `ACKNOWLEDGED` are requested separately, or everything is requested and the `RESOLVED` ones are discarded. Cursor pagination: `first`, `after` and `pageInfo { hasNextPage, endCursor }`.

**Real time**

| `/ws` message | Effect on screen |
| --- | --- |
| `telemetry.tick` | Updates the raw value of a metric. It carries the metric, not the derived sign: `pio2` does not arrive through ticks. |
| `alert.raised` | The alert panel appears and `dashboard` is requested again. |
| `alert.updated` (`status: acknowledged`) | Shows "Alert acknowledged". |
| `alert.resolved` | Removes the panel and `dashboard` is requested again. |
| `recommendation.ready` | The template recommendation with citations arrives; `alert(id)` is requested again. |
| `recommendation.enriched` | Replaces the text with the version written by the model (`composed_by: "llm"`). |

**Recommended strategy:** request `dashboard` on opening, on receiving any `alert.*` and every 5 to 10 s. Ticks serve the charts (4.2), not rebuilding the status light.

**States:** no connection to the backend → "No connection to the ship"; no readings → "No data yet"; no alerts → only the status light.

### 4.2 Facility

**Demo mode (visible in `dev1`, `dev2` and `jury`)**

| Element | Action | Call |
| --- | --- | --- |
| Trigger a scenario | Choose scenario and zone | `POST /api/v1/sim/scenarios/{key}:start` with body `{ "zone": "lab", "speed": 1 }` |
| Normalize | Stops the scenario | `POST /api/v1/sim/scenarios/{key}:stop` with `{ "zone": "lab" }` |

Backend scenario keys and their button in the front end:

| Front-end button (`DemoPanel`) | Backend key |
| --- | --- |
| Pressure leak | `pressure_leak` |
| High CO₂ | `co2_slow` |
| Humidity | `humidity_high` |
| O₂ failure | `o2_failure` |
| Heat | `heat` |

`zone` is the zone **code** (`lab`, `eng`...), not its id. `speed` goes from 0 (excluded) to 20. On start, an unknown key answers 404 and an unknown zone 422, with `detail`. On stop only the zone is validated; stopping a scenario that is not active gives no error.

**Ship floor plan**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Drawn zones | `zones[]`: `id`, `code`, `name`, `kind`, `deck`, `layout { x, y, w, h }` | `ship { zones }` |
| Canvas size | `canvas` (`width`, `height`) | `ship { canvas }` |
| Color of each zone | `status` (`Severity`) and `openIncidents` | `ship`, and live `zone.status` |

The floor plan is data: if the backend JSON (`data/facility/plan.json`) changes, the zones change without touching front-end code. Ten zones in the demo: engineering, life support, laboratory, infirmary, bridge, airlock, storage, gym, kitchen and sleeping quarters. A zone with `openIncidents > 0` also carries an icon.

**Charts for the selected zone**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Series per metric | `metric`, `unit`, `points[] { ts, avg, min, max }` | `zoneReadings(zoneId, metrics, from, to, resolution)` |
| Resolution | `MINUTE` (average per minute) or `RAW` (samples) | `resolution` argument |
| Available metrics | `pressure_kpa`, `o2_pct`, `co2_mmhg`, `temperature_c`, `humidity_pct` | `metrics` argument |
| New live points | `zone_id`, `metric`, `value`, `ts` | `telemetry.tick` |
| Limit lines | `rules[]`: `parameter`, `kind`, `operator`, `threshold`, `unit`, `windowS`, `severity` | `rules` (only once; the catalog does not change during the session) |

**How to draw the limits:** each `kind: "threshold"` rule is a horizontal line at `threshold`, with `operator` indicating which side the danger is on (`>` or `>=` above, `<` or `<=` below) and the color of its `severity`. `kind: "trend"` rules (`DEMO` only) have no fixed line: they are not drawn. The `parameter` says which metric it applies to: `ppco2` is `co2_mmhg`; `humidity_pct`, `temperature_c` and `pressure_kpa` match the metric; `pio2`, `n2_pct` and `pressure_rate` are derived and have no chart of their own. `windowS` is the window in seconds during which the value must be sustained (0 if instantaneous).

The charts are per zone. `pio2` is not charted (it is derived) unless the front end computes it: `PIO₂ = (kPa × 7.50062 − 47) × O₂ % / 100`.

**Tickets**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Ticket list, newest to oldest | `nodes[]`: `id`, **`code`** (`INC-0001`), `title`, `severity`, `status`, `source`, `zoneId`, `openedAt`, `valuesNormal` | `incidents(first, after, status, zoneId)` |
| Ticket detail | `description`, `type { name, categoryName }`, `sourceAlertId`, `updates[] { kind, note, at }` | `incident(id)` |
| "Values normal, can be closed" notice | `valuesNormal: true` while the ticket is still open | `incident` and `incident.updated` |

The `code` is sequential and is assigned when the ticket is opened (`INC-0001`, `INC-0002`...); the same code travels in the `incident.opened` message, so a new ticket is drawn in full without requesting the list again. States: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`. Source: `ALERT` (automatic) or `MANUAL`. **An automatic ticket never closes by itself:** when values normalize it is marked `valuesNormal` and the crew closes it.

**Actions on a ticket**

| Button | Mutation | Possible errors |
| --- | --- | --- |
| Acknowledge | `acknowledgeIncident(id)` | `NOT_FOUND`, `ALREADY_RESOLVED` |
| Resolve | `resolveIncident(id, note)` | `NOT_FOUND`, `ALREADY_RESOLVED`, **`ACTIVE_ALERTS`** (an automatic ticket is not closed while the zone has active alerts) |

**Incident catalog and report**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Catalog grouped by category | 61 types in 12 categories: `key`, `category`, `categoryName`, `name`, `detection` (`AUTO`/`MANUAL`), `defaultSeverity`, `evidenceState`, `typicalZones` (zone codes or `*`), `suggestedActions[]` | `incidentTypes(category)` |
| Report form | zone, type, optional description, optional severity | `reportIncident(zoneId, typeKey, description, severity)` |

Form rules: the default severity is the type's; `NORMAL` is not valid (`INVALID_SEVERITY`); a nonexistent zone or type gives `UNKNOWN_ZONE` or `UNKNOWN_TYPE`. A manual report does **not** replace the zone's automatic ticket.

**Real time**

| Message | Effect |
| --- | --- |
| `zone.status` | Changes the zone's color and its counter (`status`, `open_incidents`). |
| `incident.opened` | The ticket appears at the top of the list. |
| `incident.updated` | The ticket's severity, status or notice changes. |
| `incident.resolved` | The ticket becomes `RESOLVED`. |
| `scenario.changed` | Indicates that a scenario started or ended (`key`, `state`). |

### 4.3 Tasks

**What it shows**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Task list for the day, grouped | `id`, `kind`, `origin`, `title`, `zoneId`, `status`, `dueAt`, `blockedReason`, `effective`, `sourceAlertId`, `incidentId`, `templateId` | `tasks(day, kind, status)` |
| Filter | All, Health, Ship, Incidents | `kind` argument (`HEALTH`, `SHIP`, `INCIDENT`) |
| Streak | Health routines completed in the day | `streak(day)` |
| Origin of each task | `GROUND`, `SYSTEM`, `CREW` | `origin` field |
| Ground plan notice | `version`, `appliedAt`, `rejected[] { title, reason }` | `groundPlan` |
| "Tasks" consent | Whether the crew shares the state of their tasks with Ground | **No backend yet** (section 9) |

**Where each task comes from**

| Origin | When it appears | Example |
| --- | --- | --- |
| `SYSTEM` · `HEALTH`/`SHIP` | One per template and per day, when `tasks` is requested | "Measure blood pressure", "Check the laboratory filters" |
| `SYSTEM` · `INCIDENT` | When a ticket is opened; it completes itself when the ticket is resolved | "Handle: High CO₂" (`incidentId`) |
| `SYSTEM` · `HEALTH` with `sourceAlertId` | One for each recommended action for an alert | "Ventilate the zone" |
| `GROUND` | When a Ground plan is applied | "30-minute exercise" |
| `CREW` | Created by the crew | "Tidy up the storage" |

**Actions**

| Button | Mutation | Rules |
| --- | --- | --- |
| Complete | `completeTask(id, effective)` | Any origin. `effective` (`true`/`false`/`null`) answers "Did it work?". Idempotent. |
| Snooze | `snoozeTask(id, minutes)` | From 1 to 1440 minutes; 15 by default. |
| "I can't do it" | `blockTask(id, reason)` | The reason is mandatory. The task is not deleted. |
| Create | `createTask(kind, title, zoneId, dueAt)` | `HEALTH` or `SHIP` only. Origin `CREW`. Works without a ground link. |
| Edit | `updateTask(id, title, zoneId, dueAt)` | `CREW` tasks only; otherwise `NOT_EDITABLE`. |
| Delete | `deleteTask(id)` | `CREW` tasks only; otherwise `NOT_DELETABLE`. |

The front end already hides edit and delete for tasks that are not the crew's own (`canEdit`, `canDelete`); the backend rejects them anyway.

**Streak:** only completed `HEALTH` routines that are not from Ground and were not born from an alert count. The backend computes it for a single day; the front end does not need to recompute it.

**Real time (topic `crew`):** `task.assigned` (new task), `task.created` (own task), `task.completed`, `task.blocked`, `groundplan.applied` (`groundPlan` and `tasks` are requested again).

### 4.4 Assistant

**What it shows**

| Element | Datum |
| --- | --- |
| Conversation | The person's question and the answer (`text`) |
| Citations | `citations[]`: `documentCode`, `requirementRef`, `excerpt`, `evidenceState` |
| No backing | If there is no relevant passage: "I don't have that information in the loaded sources. No protocol is made up." |
| Alert note | "This answer does not change the alert." |
| Input | Text, or voice with an **editable transcription that needs confirmation** before sending |
| Voice notice | "Simulated transcription" while the fake adapter is used |

**Where it is today:** the assistant is **not in the main app** (`main.py`). Dev B tested it with their development server (`python -m spaceapp.devtools.assistant_server`, port 8000). Integration with the main app is the next step on the `testing` branch.

**Current contract** (`POST /dev/ask`, today on the development server):
- Input: `{ "text": "What happens if oxygen drops?" }`
- Output: `{ "state", "outcome": "ANSWERED" | "NO_INFO", "text", "composed_by": "template" | "llm", "degraded": boolean, "citations": [...] }`

The front end already consumes it with `askBackend(VITE_ASSISTANT_URL)`. Once it is integrated, the final route is agreed between Dev A and Dev B and published in `contracts/openapi.json`. `degraded: true` means it answered with the plain-text passages because n8n or Ollama did not respond; it is shown all the same, with a discreet note.

**Search-only alternative:** `knowledgeSearch(query, k)` returns the citable passages without composing an answer (`documentCode`, `excerpt`, `evidenceState`). It serves a protocol search box.

**Real time:** `assistant.answer` (topic `assistant`) with `utterance_id`, `text` and `citations`.

### 4.5 Ground panel (`/ground`)

It is the same application with another route (role `ground`). **It is not the crew's screen:** from here, tasks are scheduled with versioned plans that reach the ship through the ground link.

**What it shows**

| Element | Datum | Where it comes from |
| --- | --- | --- |
| Plan version on the ship | `appliedVersion` | `groundControl` |
| Active templates and their status | `templates[]`: `id`, `title`, `kind`, `status`, `blockedReason`, `cancelled` | `groundControl` |
| Plan draft | `draft { version, templates[] }` (`null` if there are no changes) | `groundControl` |
| Published plan and its stage | `published { version, stage, reason, publishedAt, ackedAt }` | `groundControl` |
| Link state | `link { online, delaySeconds, changedAt }` | `groundControl` |

**Template status** (`GroundTemplateStatus`): `PENDING` (draft only), `APPLIED`, `COMPLETED`, `BLOCKED`. The block reason (`blockedReason`) is only shown if the crew shares the "tasks" category (section 9).

**Plan pipeline** (`PlanStage`): `DRAFT` → `QUEUED` (link cut) → `IN_TRANSIT` → `RECEIVED` → `APPLIED` → `CONFIRMED`. A plan can also end up `REJECTED` (with `reason`). While there is an unconfirmed plan, another cannot be published.

**Actions**

| Button | Mutation | Errors |
| --- | --- | --- |
| Add template | `saveGroundTemplate(title, kind, zoneCode, recurrence, templateId)` | `TITLE_REQUIRED`, `INVALID_KIND` |
| Cancel template | `cancelGroundTemplate(templateId)` | `NOT_FOUND` |
| Publish plan | `publishGroundPlan` | `NOTHING_TO_PUBLISH`, `PLAN_IN_FLIGHT` |
| Cut or restore link | `setGroundLink(online, delaySeconds)` | — |

All of them return the full view (`GroundControlView`) or a `GroundError`. `kind` only accepts `HEALTH` or `SHIP`. `zoneCode` is the zone code (`lab`). `recurrence` is `DAILY` (default) or `ONE_TIME`. Cancelling a template that only exists in the draft removes it; one that is already applied is marked `cancelled` and is withdrawn from the ship when the plan is applied. What the crew has already completed is not lost.

**Real time (topic `crew`):** `groundplan.received`, `groundplan.applied`, `groundplan.confirmed` and `groundlink.state` (`UP`/`DOWN`, `queued`). With these the pipeline advances without polling.

## 5. `/ws` messages

**Format.** Every server message is `{ "seq", "topic", "type", "at", "data" }`.
- `seq` is the outbox id when the message comes from an event; in ticks and in the `system` topic it is `null`.
- The `data` and field names of the messages are in `snake_case`, unlike GraphQL.

**Topics:** `telemetry`, `alerts`, `habitat`, `crew`, `assistant`. A new client is subscribed to **all** of them. Client messages:

| Message | Response |
| --- | --- |
| `{ "type": "subscribe", "topics": [...] }` / `unsubscribe` | `subscribed` with the list of current topics |
| `{ "type": "resume", "after_outbox_id": N }` | The missed messages with `seq > N`, in order, and then `resumed { count, last_seq }`. 24 h retention. |
| `{ "type": "ping", "ts": ... }` | `pong` with the same `ts` |
| (any other) | `error { reason }`; the connection stays open |

The server sends `ping` if 15 s pass without messages.

**Catalog**

| Topic | `type` | `data` fields |
| --- | --- | --- |
| `telemetry` | `telemetry.tick` | `zone_id`, `sensor_id`, `metric`, `value`, `ts` |
| `telemetry` | `scenario.changed` | `key`, `state`, `speed`, `zone_id` |
| `alerts` | `alert.raised` | `alert_id`, `zone_id`, `rule_key`, `severity`, `evidence_state`, `cause_hint`, `evidence` |
| `alerts` | `alert.updated` | `alert_id`, `status` (`acknowledged`), `at` |
| `alerts` | `alert.resolved` | `alert_id`, `status` (`resolved`), `resolved_at`, `duration_s` |
| `alerts` | `recommendation.ready` | `alert_id`, `recommendation_id`, `action_keys`, `citations`, `composed_by: "template"` |
| `alerts` | `recommendation.enriched` | `recommendation_id`, `text`, `composed_by: "llm"` |
| `habitat` | `incident.opened` | `incident_id`, `code`, `zone_id`, `severity`, `title`, `description`, `source`, `status` |
| `habitat` | `incident.updated` | `incident_id`, `severity`, `status`, `note` |
| `habitat` | `incident.resolved` | `incident_id`, `zone_id`, `resolved_at`, `status` |
| `habitat` | `zone.status` | `zone_id`, `status`, `open_incidents` |
| `crew` | `task.assigned` | `task_id`, `crew_member_id`, `kind`, `origin`, `action_key`, `due_at` |
| `crew` | `task.created` | `task_id`, `kind`, `title`, `zone_id`, `origin` |
| `crew` | `task.completed` | `task_id`, `action_key`, `effective` |
| `crew` | `task.blocked` | `task_id`, `origin`, `reason` |
| `crew` | `groundplan.received` | `batch_id`, `plan_version`, `changes` |
| `crew` | `groundplan.applied` | `plan_version`, `applied`, `rejected` |
| `crew` | `groundplan.confirmed` | `batch_id`, `items`, `acked_at` |
| `crew` | `groundlink.state` | `state`, `since`, `queued` |
| `assistant` | `assistant.answer` | `utterance_id`, `text`, `citations` |
| `system` | `subscribed`, `pong`, `ping`, `resumed`, `error` | depends on the case |

**Behavior the front end must respect**
- **Backpressure:** each client has a queue of 500 messages. If it fills up, the server drops ticks first; **alerts are never dropped**. A tick replaces the pending one for the same zone and metric, so only the latest value matters.
- **Reconnection:** save the last applied `seq` and send `resume` on reconnecting. Ignore any message with a `seq` less than or equal to the last one already applied (Dev B's `Stream` already does this).
- **Order:** messages with `seq` arrive in increasing order.
- **When there is no `seq`:** ticks and `system` messages. Every message born from an event (alerts, recommendations, scenarios, tickets, tasks and plans) carries `seq`.

## 6. What replaces each mock

| Dev B mock | Replaced by |
| --- | --- |
| `dashboardFor(state)` and `CabinPanel` | `dashboard(habitatId)` + `alert.*` |
| `alertFor(state)` and `AlertPanel` | `alerts(status: RAISED)` + `alert(id)` + `acknowledgeAlert` |
| `bodyIndicatorsFixture` | No replacement yet (section 9) |
| `state.zones`, `ShipPlan` | `ship { zones, canvas }` + `zone.status` |
| `zoneSeriesFor`, `ZoneCharts` | `zoneReadings` + `telemetry.tick` |
| `state.tickets`, ticket list | `incidents` + `incident.*` |
| `incidentTypesFixture`, `CatalogList` | `incidentTypes` |
| `addReportedTicket`, `ReportForm` | `reportIncident` |
| `provoke` / `normalize`, `DemoPanel` | `POST /api/v1/sim/scenarios/{key}:start` and `:stop` |
| `tasksFixture` and `app/tasks.ts` | `tasks`, `streak` and the task mutations |
| `Root.tsx` with in-memory `GroundState` | `groundControl` and the Ground mutations, plus the `groundplan.*` messages |
| `askBackend` / `mockAnswer` | Assistant route integrated into the main app |

## 7. Name and type differences between the current front end and the backend

The Spanish names the mocks used before (`z-puente`, `fuga-presion`, `co2-alto`, `humedad`, `fallo-o2`, `calor`, `RECIBIDA`, `DIARIA`, `UNA_VEZ`) were retired in the English translation: the mock scenario keys are now the backend ones and the mock zone ids are English (`z-bridge`, `z-lab`).

| Topic | Dev B's front end today | Backend |
| --- | --- | --- |
| Zone id | `z-lab`, `z-bridge` (mock) | UUID from `ship.zones[].id`; `code` (`lab`) for templates and scenarios |
| Rule thresholds | Fixed ranges inside the front end (`bands` in the artifact) | `rules { operator threshold unit windowS }`: the source is the backend |
| Scenario keys | `pressure_leak`, `co2_slow`, `humidity_high`, `o2_failure`, `heat` (same as the backend since the translation) | `pressure_leak`, `co2_slow`, `humidity_high`, `o2_failure`, `heat` |
| Visible ticket code | `t.code` (for example "INC-001") | `code` with **four digits** (`INC-0001`). Adjust if the front end or its tests expect three |
| Ground template status | `PENDING`, `RECEIVED`, `APPLIED`, `COMPLETED`, `BLOCKED` | `PENDING`, `APPLIED`, `COMPLETED`, `BLOCKED`: **`RECEIVED` does not exist** |
| Plan stage | `QUEUED`, `IN_TRANSIT`, `RECEIVED`, `APPLIED`, `CONFIRMED` | The same, plus `DRAFT` and **`REJECTED`** (the front end must show it) |
| Template kind | `HEALTH` or `SHIP` | `TaskKind` includes `INCIDENT`, but a template only accepts `HEALTH` or `SHIP` |
| Snooze | `snoozeTask(minutes)` | `snoozeTask(id, minutes)` (`snoozeReminder` does not exist) |
| Field names | `camelCase` | GraphQL in `camelCase`; the `/ws` `data` in `snake_case` |
| Severity | `NORMAL`, `ATTENTION`, `ALERT`, `CRITICAL` | Same (in `/ws` it is also uppercase) |
| `evidence` of an alert | — | Free object (`JSON`) with `parameter`, `value`, `unit`, `operator`, `threshold`, `window_s`, `band`, `source_requirement`, `source_document`, `evidence_state`. Show whichever exist. |

## 8. Recommended order for connecting

1. **Proxy and types:** add a proxy for `/graphql`, `/api` and `/ws`; generate types from `contracts/`.
2. **Cabin:** `dashboard` + `alerts` + `acknowledgeAlert` + `alert.*` messages. It is the first thing the jury sees.
3. **Facility:** `ship`, `incidents`, `incidentTypes`, `reportIncident`, `zoneReadings`, `zone.status` and `incident.*` messages, and demo mode.
4. **Tasks:** `tasks`, `streak` and the mutations; `task.*` messages.
5. **Ground panel:** `groundControl` and the mutations; `groundplan.*` messages.
6. **Assistant:** when Dev A connects it to the main app.

At each step, remove the corresponding mock and leave the tests against recorded real responses (the contracts are in `contracts/`).

## 9. What the backend does not have yet

| Gap | Effect on the front end | What is proposed |
| --- | --- | --- |
| **Human body** (6 indicators) | There is no telemetry or baseline for the body. | Keep `bodyIndicatorsFixture` labeled `DEMO`. It is what the plan asks for while the Crew module does not exist. |
| **"Tasks" consent** | The switch is not saved in the backend. | Local front-end state. Ground sees the tasks' block reason unfiltered. |
| **Baseline and crew member profiles** (`crewMember`, `recordBaseline`, `setConsent`) | They do not exist. All tasks belong to a demonstration crew member. | Pending the Crew module (F15). |
| **Authentication of the `ground` role** | Anyone who opens `/ground` sees the panel. | Acceptable for the demo; declared in the delivery. |
| **Assistant in the main app** | The front end uses the development server. | Integration on `testing`: Dev A connects it to `main.py`. |
| **DataLoaders and cost limit** | `incident { updates }` makes one query per ticket. | Not a problem with few tickets; fixed if needed. |
| **"Active alerts" filter** | It does not exist. | Request `RAISED` and `ACKNOWLEDGED`. |
| **In-memory recommendations** | They are lost when the backend restarts. | Dev B owns the persistence. |

## 10. How to bring up the backend for testing

```bash
cd SpaceOverflow
docker compose -f docker/compose.yaml up -d --wait postgres      # PostgreSQL on port 5433
for m in platform monitoring telemetry facility engagement groundlink; do
  uv run python -m spaceapp.platform.migrate $m
done
SPACEAPP_PROFILE=dev1 SPACEAPP_RELAY_ENABLED=true SPACEAPP_SIMULATOR_AUTOSTART=true \
  SPACEAPP_RULE_WINDOW_SCALE=0.0167 \
  uv run uvicorn --factory spaceapp.main:create_app --port 8001
```

- `SPACEAPP_PROFILE=dev1` enables demo mode and the operations routes.
- `SPACEAPP_RELAY_ENABLED=true` turns on the outbox relay: without it no messages arrive through `/ws`.
- `SPACEAPP_SIMULATOR_AUTOSTART=true` turns on the telemetry simulator.
- `SPACEAPP_RULE_WINDOW_SCALE=0.0167` shortens the rule windows (from 1 h to about 60 s) so the demonstration is visible. `1` uses the values from the standard.
- Port 8001 avoids clashing with Dev B's assistant server (8000). Suggested Vite proxy: `/graphql`, `/api` and `/ws` to `http://127.0.0.1:8001`.
- The schema and the messages can be explored at `http://127.0.0.1:8001/graphql` (GraphiQL) and `/docs` (REST).
