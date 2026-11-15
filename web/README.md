# web · health monitor interface

Crew interface (SPA). **Decision-support prototype: not a medical device.** Every value without a verified source is labeled `DEMO`, and body data additionally carries the "simulated" mark.

## Status

Runs on **demo data**: no backend is connected yet (GraphQL and `/ws` arrive at milestone I2 with Dev A). Views: **Cabin**, **Ship** and **Assistant**.

## Commands

```bash
npm run dev            # development server
npm test               # tests (Vitest, jsdom)
npm run test:coverage  # coverage, 80 % threshold
npm run lint           # ESLint
npm run typecheck      # TypeScript without emitting
npm run codegen        # types from ../contracts/schema.graphql
npm run build          # production build
```

## Structure

- `src/app/`: pure demo state (`scenario.ts`).
- `src/features/cabin`, `ship`, `assistant`, `charts`: panels by feature.
- `src/shared/`: base components (`SevPill`, `EvidenceBadge`, `Banner`) and color tokens.
- `src/data/`: mocks (MSW, fixtures, WS recordings) and the `/ws` message queue.

## Rules it follows

- Color is never alone: every status carries a symbol and text (● Normal, ▲ Attention, ◆ Alert, ■ Critical).
- The interface shows what the backend computes and does not recompute it (for example PIO₂).
- The assistant may name an active alert and never changes it.

## Pending

`useWs` hook and real GraphQL mutations (I2), the full catalog of 61 incident types, the SVG body silhouette, network error states. The `../contracts/schema.graphql` contract is a **draft** pending Dev A's review.
