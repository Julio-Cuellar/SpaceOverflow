# Odyssey web application

English React / Vite / TypeScript mission console and personal astronaut workspace, built from the approved mockups. Fonts, portraits and styles are bundled locally.

```bash
npm ci
npm run dev
```

Open `/` for Mission Control and `/dashboard-tripulation` directly for the personal astronaut dashboard. The personal dashboard is not a control-center sidebar entry. Other routes: `/crew`, `/habitat`, `/tasks`, `/assistant`, `/ground`, `/settings`.

## Data adapters

The header shows the current source. **Demo** is an explicit in-memory simulation. **Backend** consumes the configured GraphQL, REST and WebSocket services; failures never silently become demo data. The assistant/voice adapter is configured separately and can use the real service while mission telemetry remains simulated.

Copy `.env.example` to `.env` and set the available services. No frontend environment variable may contain a secret. The current checkout has the assistant development server and core telemetry/rules REST adapters; Dev A's complete GraphQL gateway and crew authentication are not yet in this checkout.

```bash
SPACEAPP_API_PROXY=http://127.0.0.1:8002 \
SPACEAPP_ASSISTANT_PROXY=http://127.0.0.1:8000 npm run dev
```

Backend personal mode requires `VITE_SESSION_URL`, implementing the authenticated current-user response documented in [the integration handoff](../docs/FRONTEND_INTEGRATION.md). Until then, no personal data is inferred from the global dashboard. Route visibility alone does not enforce authorization.

## Checks

```bash
npm run codegen               # exported backend schema, or explicit integration target
npm run contracts:check       # query/mutation consistency
npm run contracts:merge-check # additionally requires Dev A's real schema export
npm run typecheck
npm run lint
npm test
npm run build                 # includes codegen; output in dist/
```

`npm run format` formats the new application and configuration. Node 22.18 or newer is required. The build includes local fonts and illustrative portraits. The static host must use an SPA history fallback; Vite's development proxy is not part of the production bundle.

## Code layout

- `src/console/model.ts`: view models, gateway port, commands and English enum labels.
- `src/console/data/`: backend adapter, demonstration adapter, operation documents, state loading, realtime and voice.
- `src/console/pages/`: mission overview, habitat, Ground, personal dashboard and settings.
- `src/console/ui/`: cards, body outline, dialogs, tasks, incidents, trends and agent.
- `src/features/assistant/`: existing backend text/voice adapters and microphone support.
- `src/LegacyRoot.tsx`, `src/App.tsx`: unmounted previous implementation retained for regression tests.
- `mockup/`, `dashboard-tripulation/`: original HTML review artifacts; the active clean personal route serves the React SPA.

Voice recording works on localhost or HTTPS. Transcripts must be reviewed and confirmed. Without voice or read-aloud services, text remains available. The assistant shows retrieved citations and cannot decide or mutate alerts. The interface does not calculate clinical thresholds or confidence scores.

See [the architecture review and Dev A handoff](../docs/FRONTEND_INTEGRATION.md) for current availability, exact integration boundaries, production serving and merge acceptance checks.
