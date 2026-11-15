import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LegacyRoot as Root } from './LegacyRoot'

describe('Root', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => vi.useRealTimers())

  it('opens the crew app on "/"', () => {
    render(<Root initialPath="/" />)

    expect(screen.getByRole('tab', { name: 'Cabin' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: /Ground panel/ })).not.toBeInTheDocument()
  })

  it('opens the Earth control panel on "/ground"', () => {
    render(<Root initialPath="/ground" />)

    expect(screen.getByRole('heading', { name: 'Ground panel (control center)' })).toBeVisible()
    expect(screen.queryByRole('tab', { name: 'Cabin' })).not.toBeInTheDocument()
  })

  it('takes a plan from the draft to applied, and the ship then says "Plan v4 applied"', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/ground" />)

    await user.type(screen.getByLabelText('Template title'), 'Weight check')
    await user.click(screen.getByRole('button', { name: 'Add template' }))
    await user.click(screen.getByRole('button', { name: 'Publish plan v4' }))
    expect(within(screen.getByRole('list', { name: 'Plan status v4' })).getByText('In transit')).toHaveAttribute('aria-current', 'step')

    // Demo link delay: 2 s per step (link → received → applied → confirmed).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000)
    })
    expect(within(screen.getByRole('list', { name: 'Plan status v4' })).getByText('Confirmed')).toHaveAttribute('aria-current', 'step')

    await user.click(screen.getByRole('link', { name: 'Go to the ship' }))
    expect(screen.getByRole('status', { name: 'Ground plan' })).toHaveTextContent('Plan v4 applied')
  })

  it('keeps the plan queued while the link is cut and delivers it when it is restored', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/ground" />)

    await user.click(screen.getByRole('button', { name: 'Cortar enlace' }))
    await user.type(screen.getByLabelText('Template title'), 'Weight check')
    await user.click(screen.getByRole('button', { name: 'Add template' }))
    await user.click(screen.getByRole('button', { name: 'Publish plan v4' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(screen.getByText(/Queued: no link with the ship/)).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Restablecer enlace' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000)
    })

    expect(within(screen.getByRole('list', { name: 'Plan status v4' })).getByText('Confirmed')).toHaveAttribute('aria-current', 'step')
  })

  it('hides the task status from Earth when the crew stops sharing the "tareas" category', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<Root initialPath="/" />)

    await user.click(screen.getByRole('tab', { name: 'Tasks' }))
    await user.click(screen.getByRole('checkbox', { name: 'Share the status of my tasks with Ground' }))
    await user.click(screen.getByRole('link', { name: 'Ground panel' }))

    expect(screen.getByText(/The crew does not share the status of its tasks/)).toBeVisible()
  })
})

describe('Root with the real assistant', () => {
  it('hands the assistant to the ship so its questions do not use the simulation', async () => {
    const askAssistant = vi.fn().mockResolvedValue({ outcome: 'NO_INFO', text: 'No data.', citations: [] })
    render(<Root initialPath="/" askAssistant={askAssistant} />)
    await userEvent.click(screen.getByRole('tab', { name: 'Assistant' }))

    await userEvent.type(screen.getByLabelText('Question'), 'question')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('No data.')).toBeInTheDocument()
  })
})
