# Astronaut workspace UX

## Scope and entry

The standalone prototype is served at `/dashboard-tripulation` by the Vite development server. Open it directly; it is not an entry in the Mission Control sidebar. `/mockup/` remains the control-center concept. This page extends the same visual system: atmospheric cyan (#65B5CB), blue surfaces, sharp controls, Montserrat headings and Roboto text. The round assistant launcher is intentionally distinct.

The entry experience represents A. Garcia after sign-in. Identity is visible in the header, with no roster or astronaut switcher. The prototype does not implement login, authentication, server authorization, medical scoring or live telemetry. It contains fictional, local fixtures and no other astronaut's personal measurements. Form changes and conversation last only until page reload.

## Information ownership

| Content | Scope | Production requirement |
| --- | --- | --- |
| My health | Current authenticated astronaut | Server must derive identity from the session; never rely on a client user ID for authorization. |
| My tasks and routine | Assigned to the authenticated astronaut | Apply the same server-side ownership rules to reads and mutations. |
| My tickets | Reported by or assigned to this astronaut | Protect private descriptions and updates. Shared zone tickets remain in a separate section. |
| My habitat | Current permitted work zone | Resolve zone membership and permissions on the server, including incident details. |
| Assistant | Current user and authorized zone context | Retrieve only permitted sources and conversations. Never load another astronaut's health context. |

The mockup filters local tasks and tickets by its fixed demo identity to communicate the intended UX; this is not a security boundary. V2 does not yet provide real crew profiles or per-user task ownership. The production redesign requires backend identity, ownership and zone-membership contracts before these rules can be enforced.

## Page organization and navigation

A compact sticky header contains local anchors: **My day**, **My habitat**, and **My routine**. They move within the personal dashboard and do not grant control-center access. The active anchor follows the visible section. The top right identifies the current session. The first screen prioritizes personal health and the next activity, followed by task and ticket queues. Habitat telemetry follows, then the full routine. The floating assistant stays in the lower right on every section.

The page uses a bounded content width and CSS grids, without scaling text or stretching cards across unlimited widths. Desktop presents health beside the next activity and task/ticket lists side by side. Tablet stacks the overview and preserves paired queues where readable. Mobile uses a single column, compact identity, two-column measurement grids, and a vertical routine. Dialogs keep actions within the viewport. Keyboard focus is visible, dialogs support Escape and return focus, and status is always named in text.

## Panel behaviors

| Panel | Information hierarchy | Main interaction | Empty / failure behavior |
| --- | --- | --- | --- |
| My health | Personal identity, named status, measurement labels, units, capture time | Read personal heart rate, SpO₂, body temperature, daily radiation exposure and blood pressure | Loading and unavailable readings are withheld; offline readings are explicitly cached. Personal blood pressure is separate from habitat pressure. |
| Next activity | Activity name, start, duration, location | Open the corresponding task detail or jump to the routine | When all tasks are complete, show completion and a link to review the routine. |
| My tasks | Pending count, completion summary, filters, assigned items | Complete or reopen a task; inspect time, location and source | No pending/completed items message depends on filter. Mutation is disabled offline. The same state powers routine completion. |
| My tickets | Open count, filters, ticket code and status, title, origin, severity | Inspect a ticket or create a personal report | Resolved filter has its own empty state. Report form validates title, location and observation and adds a clearly labeled local demo ticket. |
| My habitat | Current zone, schematic location, environmental readings, shared incidents | Open the laboratory incident without adding it to the personal ticket queue | Cached timestamp when offline; hide readings on data failure. Shared incidents are not cleared by the personal empty-state preview. |
| My routine | Time order, duration, location, completion state | Open the same task detail used by My tasks | Completion is synchronized, rather than recorded in a second independent list. Incident tasks are not rewarded as wellness streaks. |
| Mission assistant | Current-user/zone context, conversation, source availability | Round launcher opens a side dialog; suggestions and text submission | Closing retains the conversation for the current page session. Requests are unavailable offline. Responses explicitly identify local fixtures or missing sources. |

Environmental readings include oxygen, CO₂, temperature, pressure, humidity and PIO₂. Sensor labels clearly distinguish shared habitat data from personal wearable measurements. Fictional zone values are consistent with the fictional zone incident. Severity and evidence are separate labels; no clinical thresholds or wellness percentages are inferred.

## Key journeys

1. Open the personal route → recognize the signed-in identity → review personal health and next activity.
2. Open a task → inspect assignment and location → mark complete → see the pending count and routine update together.
3. Open a personal ticket → inspect its status and ownership; or submit a local demo report → see it in the open queue.
4. Jump to My habitat → inspect zone measurements and the shared laboratory incident → open its details.
5. Jump to My routine → review the chronological schedule → open an activity using the same task workflow.
6. Invoke the floating assistant → ask about the next pending activity or zone incidents → review the stated demo source → close and resume the same page.

## Review states

The prototype-only **Preview state** selector exposes Connected, Offline, No pending items, Loading and Data unavailable. It is a review tool, not a production navigation element. Offline blocks submissions and labels cached data. Error hides sensor values; reconnect restores the simulated dataset. Empty-state preview changes the presentation without rewriting the actual task fixture. A persistent simulation notice remains visible at the top.

## Integration boundaries and next decisions

- Keep role landing routes separate: crew sign-in lands at `/dashboard-tripulation`; control-center roles land in their authorized dashboard. Do not implement role selection as a public crew menu item.
- Bind personal queries, task actions and conversation context to authenticated identity. Reject another user's resource IDs on the server.
- Connect task and incident actions to the V2 GraphQL contracts and live updates to WebSocket events; REST assistant integration follows separately. This prototype does not call these services.
- Replace fictional status labels and blood-pressure/radiation fixtures only when sensor contracts, units and validated interpretation rules exist.
- In production, ticket severity comes from the configured incident type. The demo report uses an explicitly disclosed placeholder and does not implement escalation, acknowledgement or incident resolution.
- Serve the standalone HTML route explicitly in a future production build or integrate the approved design into the app router. The current Vite rewrite is development-only; `npm run build` does not package this isolated mockup.

## Review checklist

- Direct route works without a sidebar entry in Mission Control.
- Exactly one astronaut identity and personal health profile appear.
- Task filters, completion, routine sync, ticket filters, details and demo reporting are navigable.
- Shared zone incidents never imply access to other astronauts' private data.
- Assistant opens from the lower-right round button and preserves its conversation when closed.
- Desktop, tablet and phone layouts retain readable units and reachable actions.
- Loading, empty, offline and error presentations can be inspected independently.
