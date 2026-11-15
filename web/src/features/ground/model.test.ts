import { describe, expect, it } from 'vitest'
import {
  addTemplate,
  advancePlan,
  hasChanges,
  initialGroundState,
  markForCancel,
  publishPlan,
  setLink,
} from './model'

const withDraft = () => addTemplate(initialGroundState(), { title: 'Control de peso', kind: 'SALUD' }, 'tpl-new')

describe('initial state', () => {
  it('starts with the plan applied and confirmed, the link up, and no draft', () => {
    const state = initialGroundState()

    expect(state.version).toBe(3)
    expect(state.published?.stage).toBe('CONFIRMADO')
    expect(state.link.online).toBe(true)
    expect(state.draft).toBeNull()
  })
})

describe('draft of the next version', () => {
  it('opens the next version when a template is added, keeping the active ones', () => {
    const state = withDraft()

    expect(state.draft?.version).toBe(4)
    expect(state.draft?.templates).toHaveLength(initialGroundState().templates.length + 1)
    expect(hasChanges(state)).toBe(true)
  })

  it('ignores a template without title', () => {
    const state = addTemplate(initialGroundState(), { title: '  ', kind: 'NAVE' }, 'x')

    expect(state.draft).toBeNull()
  })

  it('marks an active template for cancellation without removing it', () => {
    const base = initialGroundState()
    const target = base.templates[0]?.id ?? ''

    const state = markForCancel(base, target)

    expect(state.draft?.templates.find((t) => t.id === target)?.cancelled).toBe(true)
    expect(state.templates.find((t) => t.id === target)?.cancelled).toBe(false)
  })

  it('drops a template added to the draft when it is marked before publishing', () => {
    const state = markForCancel(withDraft(), 'tpl-new')

    expect(state.draft?.templates.some((t) => t.id === 'tpl-new')).toBe(false)
    expect(hasChanges(state)).toBe(false)
  })

  it('has no changes when nothing differs from the active plan', () => {
    expect(hasChanges(initialGroundState())).toBe(false)
  })
})

describe('publishing', () => {
  it('does nothing when there is no change to publish', () => {
    const state = initialGroundState()

    expect(publishPlan(state)).toEqual(state)
  })

  it('sends the plan over the link and moves through the pipeline until confirmed', () => {
    let state = publishPlan(withDraft())
    expect(state.published).toEqual({ version: 4, stage: 'EN_EL_ENLACE' })
    expect(state.draft).toBeNull()

    state = advancePlan(state)
    expect(state.published?.stage).toBe('RECIBIDO')
    expect(state.version).toBe(3)

    state = advancePlan(state)
    expect(state.published?.stage).toBe('APLICADO')
    expect(state.version).toBe(4)

    state = advancePlan(state)
    expect(state.published?.stage).toBe('CONFIRMADO')
  })

  it('queues the plan when the link is cut and delivers it when the link comes back', () => {
    let state = publishPlan(setLink(withDraft(), { online: false }))
    expect(state.published).toEqual({ version: 4, stage: 'EN_COLA' })

    state = advancePlan(state)
    expect(state.published?.stage).toBe('EN_COLA')

    state = setLink(state, { online: true })
    expect(state.published?.stage).toBe('EN_EL_ENLACE')
  })

  it('applies the new templates and removes the cancelled ones only when the plan is applied', () => {
    const base = initialGroundState()
    const cancelled = base.templates[0]?.id ?? ''
    let state = markForCancel(addTemplate(base, { title: 'Control de peso', kind: 'SALUD' }, 'tpl-new'), cancelled)
    state = publishPlan(state)
    expect(state.templates.some((t) => t.id === cancelled)).toBe(true)

    state = advancePlan(advancePlan(state))

    expect(state.templates.some((t) => t.id === cancelled)).toBe(false)
    expect(state.templates.find((t) => t.id === 'tpl-new')?.status).toBe('APLICADA')
  })

  it('ignores a second publish while the first plan is still on its way', () => {
    const first = publishPlan(withDraft())
    const again = publishPlan(addTemplate(first, { title: 'Otra', kind: 'NAVE' }, 'tpl-2'))

    expect(again.published).toEqual(first.published)
  })
})

describe('link control', () => {
  it('keeps the delay chosen for the demo', () => {
    expect(setLink(initialGroundState(), { delaySeconds: 5 }).link.delaySeconds).toBe(5)
  })
})
