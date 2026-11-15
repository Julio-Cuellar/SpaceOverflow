import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TaskList } from './TaskList'
import type { Task } from './model'

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    kind: 'HEALTH',
    origin: 'SYSTEM',
    title: 'Measure blood pressure',
    zoneId: null,
    status: 'PENDING',
    dueAt: '2026-11-14T12:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
    ...overrides,
  }
}

const zones = [{ id: 'z-lab', name: 'Laboratory' }]

function renderList(tasks: Task[], handlers: Partial<Parameters<typeof TaskList>[0]> = {}) {
  const props = {
    onComplete: vi.fn(),
    onBlock: vi.fn(),
    onSnooze: vi.fn(),
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
    ...handlers,
  }
  render(<TaskList tasks={tasks} zones={zones} {...props} />)
  return props
}

describe('TaskList', () => {
  it('shows the origin tag on every card', () => {
    renderList([
      task({ id: 'a', origin: 'GROUND', title: 'Exercise' }),
      task({ id: 'b', origin: 'CREW', title: 'Check filter', kind: 'SHIP' }),
    ])

    expect(within(screen.getByRole('listitem', { name: /Exercise/ })).getByText('Ground')).toBeVisible()
    expect(
      within(screen.getByRole('listitem', { name: /Check filter/ })).getByText('Crew'),
    ).toBeVisible()
  })

  it('filters by kind', async () => {
    renderList([
      task({ id: 'a', title: 'Rutina de salud' }),
      task({ id: 'b', kind: 'SHIP', title: 'Cambiar filtro' }),
    ])

    await userEvent.click(screen.getByRole('button', { name: 'Ship' }))

    expect(screen.queryByText('Rutina de salud')).not.toBeInTheDocument()
    expect(screen.getByText('Cambiar filtro')).toBeVisible()
  })

  it('offers the four filters and starts on "Todas"', () => {
    renderList([task()])

    expect(screen.getByRole('button', { name: 'Todas' })).toHaveAttribute('aria-pressed', 'true')
    for (const name of ['Health', 'Ship', 'Incidents']) {
      expect(screen.getByRole('button', { name })).toBeVisible()
    }
  })

  it('does not offer edit or delete on a task from Earth', () => {
    renderList([task({ origin: 'GROUND' })])

    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Complete' })).toBeVisible()
  })

  it('offers edit and delete on the crew own task and reports the deletion', async () => {
    const { onDelete } = renderList([task({ id: 'own', origin: 'CREW' })])

    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onDelete).toHaveBeenCalledWith('own')
    expect(screen.getByRole('button', { name: 'Edit' })).toBeVisible()
  })

  it('edits the title of its own task', async () => {
    const { onUpdate } = renderList([task({ id: 'own', origin: 'CREW', title: 'Antes' })])

    await userEvent.click(screen.getByRole('button', { name: 'Edit' }))
    const input = screen.getByLabelText('Title')
    await userEvent.clear(input)
    await userEvent.type(input, 'Later')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(onUpdate).toHaveBeenCalledWith('own', { title: 'Later', zoneId: null })
  })

  it('asks "Did it work?" when completing and reports the answer', async () => {
    const { onComplete } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Complete' }))
    expect(screen.getByText('Did it work?')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Yes' }))

    expect(onComplete).toHaveBeenCalledWith('a', true)
  })

  it('lets the crew say it does not know whether it worked', async () => {
    const { onComplete } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Complete' }))
    await userEvent.click(screen.getByRole('button', { name: 'Not sure' }))

    expect(onComplete).toHaveBeenCalledWith('a', null)
  })

  it('requires a reason to block a task', async () => {
    const { onBlock } = renderList([task({ id: 'a', origin: 'GROUND' })])

    await userEvent.click(screen.getByRole('button', { name: 'No puedo cumplirla' }))
    expect(screen.getByRole('button', { name: 'Confirmar bloqueo' })).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Reason'), 'Missing equipment')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar bloqueo' }))

    expect(onBlock).toHaveBeenCalledWith('a', 'Missing equipment')
  })

  it('postpones the reminder', async () => {
    const { onSnooze } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Posponer 30 min' }))

    expect(onSnooze).toHaveBeenCalledWith('a', 30)
  })

  it('keeps a blocked task visible with its reason and no more actions', () => {
    renderList([task({ status: 'BLOCKED', blockedReason: 'Missing equipment' })])

    expect(screen.getByText(/Missing equipment/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Complete' })).not.toBeInTheDocument()
  })

  it('shows whether a completed measure worked', () => {
    renderList([
      task({ id: 'a', status: 'COMPLETED', effective: true }),
      task({ id: 'b', status: 'COMPLETED', effective: false, title: 'Otra' }),
    ])

    expect(screen.getByText('It worked')).toBeVisible()
    expect(screen.getByText('It did not work')).toBeVisible()
  })

  it('shows the streak and says what does not count', () => {
    renderList([
      task({ id: 'a', status: 'COMPLETED' }),
      task({ id: 'b', status: 'COMPLETED', origin: 'GROUND', title: 'From Ground' }),
      task({ id: 'c', status: 'COMPLETED', sourceAlertId: 'x', title: 'De alerta' }),
    ])

    expect(screen.getByText('Streak: 1')).toBeVisible()
    expect(screen.getByText(/Critical alerts do not add points/)).toBeVisible()
  })
})
