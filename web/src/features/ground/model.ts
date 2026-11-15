/** State of a template on the ship, as Ground sees it (plan, 11.2). */
export type TemplateStatus = 'PENDING' | 'RECEIVED' | 'APPLIED' | 'COMPLETED' | 'BLOCKED'

/** Pipeline of a published plan (plan, 11.3). `QUEUED` is the plan held back while the link is cut. */
export type PlanStage = 'QUEUED' | 'IN_TRANSIT' | 'RECEIVED' | 'APPLIED' | 'CONFIRMED'

export interface GroundTemplate {
  id: string
  title: string
  kind: 'HEALTH' | 'SHIP'
  status: TemplateStatus
  /** Reason the crew gave when blocking it. Only visible if they share the "tasks" category. */
  blockedReason: string | null
  /** Marked to cancel in the draft. It is removed from the ship when the plan is applied. */
  cancelled: boolean
}

export interface Draft {
  version: number
  templates: GroundTemplate[]
}

export interface PublishedPlan {
  version: number
  stage: PlanStage
}

export interface GroundState {
  /** Version of the plan applied on the ship. */
  version: number
  templates: GroundTemplate[]
  draft: Draft | null
  /** Published plan not yet confirmed, or the last confirmed one. */
  published: PublishedPlan | null
  /** Draft already published, waiting to be applied on the ship. */
  pending: Draft | null
  link: { online: boolean; delaySeconds: number }
}

/** Demo data (not from NASA): a v3 plan already applied on the ship. */
export function initialGroundState(): GroundState {
  return {
    version: 3,
    templates: [
      { id: 'tpl-ejercicio', title: '30-minute exercise', kind: 'HEALTH', status: 'COMPLETED', blockedReason: null, cancelled: false },
      { id: 'tpl-filtros', title: 'Check the CO₂ filters', kind: 'SHIP', status: 'APPLIED', blockedReason: null, cancelled: false },
      { id: 'tpl-sueno', title: 'Sleep log', kind: 'HEALTH', status: 'BLOCKED', blockedReason: 'No sensor available', cancelled: false },
    ],
    draft: null,
    published: { version: 3, stage: 'CONFIRMED' },
    pending: null,
    link: { online: true, delaySeconds: 2 },
  }
}

function openDraft(state: GroundState): Draft {
  return (
    state.draft ?? {
      version: state.version + 1,
      templates: state.templates.map((t) => ({ ...t, cancelled: false })),
    }
  )
}

export function addTemplate(
  state: GroundState,
  template: { title: string; kind: 'HEALTH' | 'SHIP' },
  id: string,
): GroundState {
  const title = template.title.trim()
  if (title === '') return state
  const draft = openDraft(state)
  return {
    ...state,
    draft: {
      ...draft,
      templates: [
        ...draft.templates,
        { id, title, kind: template.kind, status: 'PENDING', blockedReason: null, cancelled: false },
      ],
    },
  }
}

/** Marks an active template to cancel; if it only existed in the draft, it removes it. */
export function markForCancel(state: GroundState, templateId: string): GroundState {
  const draft = openDraft(state)
  const isActive = state.templates.some((t) => t.id === templateId)
  return {
    ...state,
    draft: {
      ...draft,
      templates: isActive
        ? draft.templates.map((t) => (t.id === templateId ? { ...t, cancelled: true } : t))
        : draft.templates.filter((t) => t.id !== templateId),
    },
  }
}

export function hasChanges(state: GroundState): boolean {
  const { draft } = state
  if (draft === null) return false
  const activeIds = new Set(state.templates.map((t) => t.id))
  return draft.templates.some((t) => t.cancelled || !activeIds.has(t.id))
}

function inFlight(state: GroundState): boolean {
  return state.published !== null && state.published.stage !== 'CONFIRMED'
}

export function publishPlan(state: GroundState): GroundState {
  if (state.draft === null || !hasChanges(state) || inFlight(state)) return state
  return {
    ...state,
    published: { version: state.draft.version, stage: state.link.online ? 'IN_TRANSIT' : 'QUEUED' },
    pending: state.draft,
    draft: null,
  }
}

const NEXT_STAGE: Partial<Record<PlanStage, PlanStage>> = {
  IN_TRANSIT: 'RECEIVED',
  RECEIVED: 'APPLIED',
  APPLIED: 'CONFIRMED',
}

/** One step of the pipeline. With the plan queued it does not advance: it waits for the link to return. */
export function advancePlan(state: GroundState): GroundState {
  if (state.published === null) return state
  const next = NEXT_STAGE[state.published.stage]
  if (next === undefined) return state
  const advanced: GroundState = { ...state, published: { ...state.published, stage: next } }
  if (next !== 'APPLIED' || state.pending === null) return advanced
  return {
    ...advanced,
    version: state.pending.version,
    templates: state.pending.templates
      .filter((t) => !t.cancelled)
      .map((t) => (state.templates.some((a) => a.id === t.id) ? t : { ...t, status: 'APPLIED' })),
    pending: null,
  }
}

export function setLink(
  state: GroundState,
  change: { online?: boolean; delaySeconds?: number },
): GroundState {
  const link = { ...state.link, ...change }
  const restored = change.online === true && state.published?.stage === 'QUEUED'
  return {
    ...state,
    link,
    published:
      restored && state.published !== null ? { ...state.published, stage: 'IN_TRANSIT' } : state.published,
  }
}
