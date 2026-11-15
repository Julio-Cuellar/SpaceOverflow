import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Root } from './Root'

describe('Root', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => vi.useRealTimers())

  it('opens the crew app on "/"', () => {
    render(<Root initialPath="/" />)

    expect(screen.getByRole('tab', { name: 'Cabina' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: /Panel de Tierra/ })).not.toBeInTheDocument()
  })

  it('opens the Earth control panel on "/ground"', () => {
    render(<Root initialPath="/ground" />)

    expect(screen.getByRole('heading', { name: 'Panel de Tierra (centro de control)' })).toBeVisible()
    expect(screen.queryByRole('tab', { name: 'Cabina' })).not.toBeInTheDocument()
  })

  it('takes a plan from the draft to applied, and the ship then says "Plan v4 aplicado"', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/ground" />)

    await user.type(screen.getByLabelText('Título de la plantilla'), 'Control de peso')
    await user.click(screen.getByRole('button', { name: 'Añadir plantilla' }))
    await user.click(screen.getByRole('button', { name: 'Publicar plan v4' }))
    expect(within(screen.getByRole('list', { name: 'Estado del plan v4' })).getByText('En el enlace')).toHaveAttribute('aria-current', 'step')

    // Demora del enlace de la demo: 2 s por paso (enlace → recibido → aplicado → confirmado).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000)
    })
    expect(within(screen.getByRole('list', { name: 'Estado del plan v4' })).getByText('Confirmado')).toHaveAttribute('aria-current', 'step')

    await user.click(screen.getByRole('link', { name: 'Ir a la nave' }))
    expect(screen.getByRole('status', { name: 'Plan de Tierra' })).toHaveTextContent('Plan v4 aplicado')
  })

  it('keeps the plan queued while the link is cut and delivers it when it is restored', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/ground" />)

    await user.click(screen.getByRole('button', { name: 'Cortar enlace' }))
    await user.type(screen.getByLabelText('Título de la plantilla'), 'Control de peso')
    await user.click(screen.getByRole('button', { name: 'Añadir plantilla' }))
    await user.click(screen.getByRole('button', { name: 'Publicar plan v4' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(screen.getByText(/En cola: sin enlace con la nave/)).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Restablecer enlace' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000)
    })

    expect(within(screen.getByRole('list', { name: 'Estado del plan v4' })).getByText('Confirmado')).toHaveAttribute('aria-current', 'step')
  })

  it('hides the task status from Earth when the crew stops sharing the "tareas" category', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/" />)

    await user.click(screen.getByRole('tab', { name: 'Tareas' }))
    await user.click(screen.getByRole('checkbox', { name: 'Compartir el estado de mis tareas con Tierra' }))
    await user.click(screen.getByRole('link', { name: 'Panel de Tierra' }))

    expect(screen.getByText(/La tripulación no comparte el estado de sus tareas/)).toBeVisible()
  })
})

describe('Root with the real assistant', () => {
  it('hands the assistant to the ship so its questions do not use the simulation', async () => {
    const askAssistant = vi.fn().mockResolvedValue({ outcome: 'NO_INFO', text: 'Sin datos.', citations: [] })
    render(<Root initialPath="/" askAssistant={askAssistant} />)
    await userEvent.click(screen.getByRole('tab', { name: 'Asistente' }))

    await userEvent.type(screen.getByLabelText('Question'), 'question')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('Sin datos.')).toBeInTheDocument()
  })
})
