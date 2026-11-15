/** Estado de una plantilla en la nave, tal como lo ve Tierra (plan, 11.2). */
export type TemplateStatus = 'PENDIENTE' | 'RECIBIDA' | 'APLICADA' | 'COMPLETADA' | 'BLOQUEADA'

/** Canalización de un plan publicado (plan, 11.3). `EN_COLA` es el plan retenido con el enlace cortado. */
export type PlanStage = 'EN_COLA' | 'EN_EL_ENLACE' | 'RECIBIDO' | 'APLICADO' | 'CONFIRMADO'

export interface GroundTemplate {
  id: string
  title: string
  kind: 'SALUD' | 'NAVE'
  status: TemplateStatus
  /** Motivo que dio la tripulación al bloquearla. Solo se ve si comparte la categoría «tareas». */
  blockedReason: string | null
  /** Marcada para cancelar en el borrador. Se retira de la nave cuando el plan se aplica. */
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
  /** Versión del plan aplicado en la nave. */
  version: number
  templates: GroundTemplate[]
  draft: Draft | null
  /** Plan publicado que aún no se ha confirmado, o el último confirmado. */
  published: PublishedPlan | null
  /** Borrador ya publicado, a la espera de aplicarse en la nave. */
  pending: Draft | null
  link: { online: boolean; delaySeconds: number }
}

/** Datos de demostración (no de NASA): un plan v3 ya aplicado en la nave. */
export function initialGroundState(): GroundState {
  return {
    version: 3,
    templates: [
      { id: 'tpl-ejercicio', title: 'Ejercicio de 30 minutos', kind: 'SALUD', status: 'COMPLETADA', blockedReason: null, cancelled: false },
      { id: 'tpl-filtros', title: 'Revisar los filtros de CO₂', kind: 'NAVE', status: 'APLICADA', blockedReason: null, cancelled: false },
      { id: 'tpl-sueno', title: 'Registro de sueño', kind: 'SALUD', status: 'BLOQUEADA', blockedReason: 'Sin sensor disponible', cancelled: false },
    ],
    draft: null,
    published: { version: 3, stage: 'CONFIRMADO' },
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
  template: { title: string; kind: 'SALUD' | 'NAVE' },
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
        { id, title, kind: template.kind, status: 'PENDIENTE', blockedReason: null, cancelled: false },
      ],
    },
  }
}

/** Marca una plantilla activa para cancelar; si solo existía en el borrador, la quita. */
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
  return state.published !== null && state.published.stage !== 'CONFIRMADO'
}

export function publishPlan(state: GroundState): GroundState {
  if (state.draft === null || !hasChanges(state) || inFlight(state)) return state
  return {
    ...state,
    published: { version: state.draft.version, stage: state.link.online ? 'EN_EL_ENLACE' : 'EN_COLA' },
    pending: state.draft,
    draft: null,
  }
}

const NEXT_STAGE: Partial<Record<PlanStage, PlanStage>> = {
  EN_EL_ENLACE: 'RECIBIDO',
  RECIBIDO: 'APLICADO',
  APLICADO: 'CONFIRMADO',
}

/** Un paso de la canalización. Con el plan en cola no avanza: espera a que vuelva el enlace. */
export function advancePlan(state: GroundState): GroundState {
  if (state.published === null) return state
  const next = NEXT_STAGE[state.published.stage]
  if (next === undefined) return state
  const advanced: GroundState = { ...state, published: { ...state.published, stage: next } }
  if (next !== 'APLICADO' || state.pending === null) return advanced
  return {
    ...advanced,
    version: state.pending.version,
    templates: state.pending.templates
      .filter((t) => !t.cancelled)
      .map((t) => (state.templates.some((a) => a.id === t.id) ? t : { ...t, status: 'APLICADA' })),
    pending: null,
  }
}

export function setLink(
  state: GroundState,
  change: { online?: boolean; delaySeconds?: number },
): GroundState {
  const link = { ...state.link, ...change }
  const restored = change.online === true && state.published?.stage === 'EN_COLA'
  return {
    ...state,
    link,
    published:
      restored && state.published !== null ? { ...state.published, stage: 'EN_EL_ENLACE' } : state.published,
  }
}
