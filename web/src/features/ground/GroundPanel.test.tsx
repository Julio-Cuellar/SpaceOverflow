import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { GroundPanel } from './GroundPanel'
import { addTemplate, initialGroundState, publishPlan, setLink, type GroundState } from './model'

function renderPanel(state: GroundState = initialGroundState(), tasksShared = true) {
  const handlers = {
    onAddTemplate: vi.fn(),
    onCancel: vi.fn(),
    onPublish: vi.fn(),
    onLink: vi.fn(),
  }
  render(<GroundPanel state={state} tasksShared={tasksShared} {...handlers} />)
  return handlers
}

describe('GroundPanel', () => {
  it('says clearly that this is the Earth control panel and not the ship', () => {
    renderPanel()

    expect(screen.getByRole('heading', { name: 'Ground panel (control center)' })).toBeVisible()
    expect(screen.getByText(/This is not the crew screen/)).toBeVisible()
  })

  it('lists the active templates with their status in the ship when the crew shares it', () => {
    renderPanel()

    const done = screen.getByRole('listitem', { name: '30-minute exercise' })
    expect(within(done).getByText('Completada')).toBeVisible()
    const blocked = screen.getByRole('listitem', { name: 'Sleep log' })
    expect(within(blocked).getByText(/No sensor available/)).toBeVisible()
  })

  it('shows no task status when the crew does not share the "tareas" category', () => {
    renderPanel(initialGroundState(), false)

    expect(screen.getByText(/The crew does not share the status of its tasks/)).toBeVisible()
    expect(screen.queryByText('Completada')).not.toBeInTheDocument()
    expect(screen.queryByText(/No sensor available/)).not.toBeInTheDocument()
    expect(screen.getByText('30-minute exercise')).toBeVisible()
  })

  it('adds a template to the draft', async () => {
    const { onAddTemplate } = renderPanel()

    await userEvent.type(screen.getByLabelText('Template title'), 'Weight check')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Health')
    await userEvent.click(screen.getByRole('button', { name: 'Add template' }))

    expect(onAddTemplate).toHaveBeenCalledWith({ title: 'Weight check', kind: 'HEALTH' })
  })

  it('marks a template for cancellation', async () => {
    const { onCancel } = renderPanel()
    const item = screen.getByRole('listitem', { name: 'Check the CO₂ filters' })

    await userEvent.click(within(item).getByRole('button', { name: 'Mark to cancel' }))

    expect(onCancel).toHaveBeenCalledWith('tpl-filtros')
  })

  it('cannot publish without changes', () => {
    renderPanel()

    expect(screen.getByRole('button', { name: /Publish plan/ })).toBeDisabled()
  })

  it('names the next version on the publish button and publishes it', async () => {
    const draft = addTemplate(initialGroundState(), { title: 'Weight check', kind: 'HEALTH' }, 'tpl-new')
    const { onPublish } = renderPanel(draft)

    expect(screen.getByRole('heading', { name: 'Plan draft v4' })).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Publish plan v4' }))

    expect(onPublish).toHaveBeenCalled()
  })

  it('shows the whole pipeline with the current stage marked', () => {
    const state = publishPlan(addTemplate(initialGroundState(), { title: 'X', kind: 'SHIP' }, 'tpl-x'))
    renderPanel(state)

    const pipeline = screen.getByRole('list', { name: 'Plan status v4' })
    const steps = within(pipeline).getAllByRole('listitem').map((li) => li.textContent)
    expect(steps).toEqual(['Published', 'In transit', 'Received', 'Applied', 'Confirmed'])
    expect(within(pipeline).getByText('In transit')).toHaveAttribute('aria-current', 'step')
  })

  it('says the plan is queued when the link is cut', () => {
    const cut = setLink(initialGroundState(), { online: false })
    const state = publishPlan(addTemplate(cut, { title: 'X', kind: 'SHIP' }, 'tpl-x'))
    renderPanel(state)

    expect(screen.getByText(/Queued: no link with the ship/)).toBeVisible()
  })

  it('cuts and restores the link and sets the delay of the demo', async () => {
    const { onLink } = renderPanel()

    await userEvent.click(screen.getByRole('button', { name: 'Cortar enlace' }))
    await userEvent.selectOptions(screen.getByLabelText('Link delay'), '5')

    expect(onLink).toHaveBeenNthCalledWith(1, { online: false })
    expect(onLink).toHaveBeenNthCalledWith(2, { delaySeconds: 5 })
  })

  it('offers to restore a link that is cut', () => {
    renderPanel(setLink(initialGroundState(), { online: false }))

    expect(screen.getByRole('button', { name: 'Restablecer enlace' })).toBeVisible()
  })
})
