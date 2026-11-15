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

    expect(screen.getByRole('heading', { name: 'Panel de Tierra (centro de control)' })).toBeVisible()
    expect(screen.getByText(/No es la pantalla de la tripulación/)).toBeVisible()
  })

  it('lists the active templates with their status in the ship when the crew shares it', () => {
    renderPanel()

    const done = screen.getByRole('listitem', { name: 'Ejercicio de 30 minutos' })
    expect(within(done).getByText('Completada')).toBeVisible()
    const blocked = screen.getByRole('listitem', { name: 'Registro de sueño' })
    expect(within(blocked).getByText(/Sin sensor disponible/)).toBeVisible()
  })

  it('shows no task status when the crew does not share the "tareas" category', () => {
    renderPanel(initialGroundState(), false)

    expect(screen.getByText(/La tripulación no comparte el estado de sus tareas/)).toBeVisible()
    expect(screen.queryByText('Completada')).not.toBeInTheDocument()
    expect(screen.queryByText(/Sin sensor disponible/)).not.toBeInTheDocument()
    expect(screen.getByText('Ejercicio de 30 minutos')).toBeVisible()
  })

  it('adds a template to the draft', async () => {
    const { onAddTemplate } = renderPanel()

    await userEvent.type(screen.getByLabelText('Título de la plantilla'), 'Control de peso')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Salud')
    await userEvent.click(screen.getByRole('button', { name: 'Añadir plantilla' }))

    expect(onAddTemplate).toHaveBeenCalledWith({ title: 'Control de peso', kind: 'SALUD' })
  })

  it('marks a template for cancellation', async () => {
    const { onCancel } = renderPanel()
    const item = screen.getByRole('listitem', { name: 'Revisar los filtros de CO₂' })

    await userEvent.click(within(item).getByRole('button', { name: 'Marcar para cancelar' }))

    expect(onCancel).toHaveBeenCalledWith('tpl-filtros')
  })

  it('cannot publish without changes', () => {
    renderPanel()

    expect(screen.getByRole('button', { name: /Publicar plan/ })).toBeDisabled()
  })

  it('names the next version on the publish button and publishes it', async () => {
    const draft = addTemplate(initialGroundState(), { title: 'Control de peso', kind: 'SALUD' }, 'tpl-new')
    const { onPublish } = renderPanel(draft)

    expect(screen.getByRole('heading', { name: 'Borrador del plan v4' })).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Publicar plan v4' }))

    expect(onPublish).toHaveBeenCalled()
  })

  it('shows the whole pipeline with the current stage marked', () => {
    const state = publishPlan(addTemplate(initialGroundState(), { title: 'X', kind: 'NAVE' }, 'tpl-x'))
    renderPanel(state)

    const pipeline = screen.getByRole('list', { name: 'Estado del plan v4' })
    const steps = within(pipeline).getAllByRole('listitem').map((li) => li.textContent)
    expect(steps).toEqual(['Publicado', 'En el enlace', 'Recibido', 'Aplicado', 'Confirmado'])
    expect(within(pipeline).getByText('En el enlace')).toHaveAttribute('aria-current', 'step')
  })

  it('says the plan is queued when the link is cut', () => {
    const cut = setLink(initialGroundState(), { online: false })
    const state = publishPlan(addTemplate(cut, { title: 'X', kind: 'NAVE' }, 'tpl-x'))
    renderPanel(state)

    expect(screen.getByText(/En cola: sin enlace con la nave/)).toBeVisible()
  })

  it('cuts and restores the link and sets the delay of the demo', async () => {
    const { onLink } = renderPanel()

    await userEvent.click(screen.getByRole('button', { name: 'Cortar enlace' }))
    await userEvent.selectOptions(screen.getByLabelText('Demora del enlace'), '5')

    expect(onLink).toHaveBeenNthCalledWith(1, { online: false })
    expect(onLink).toHaveBeenNthCalledWith(2, { delaySeconds: 5 })
  })

  it('offers to restore a link that is cut', () => {
    renderPanel(setLink(initialGroundState(), { online: false }))

    expect(screen.getByRole('button', { name: 'Restablecer enlace' })).toBeVisible()
  })
})
