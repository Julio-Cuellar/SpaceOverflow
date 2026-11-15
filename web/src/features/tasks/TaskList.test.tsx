import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TaskList } from './TaskList'
import type { Task } from './model'

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    kind: 'SALUD',
    origin: 'SISTEMA',
    title: 'Medir la presión arterial',
    zoneId: null,
    status: 'PENDIENTE',
    dueAt: '2026-11-14T12:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
    ...overrides,
  }
}

const zones = [{ id: 'z-lab', name: 'Laboratorio' }]

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
      task({ id: 'a', origin: 'TIERRA', title: 'Ejercicio' }),
      task({ id: 'b', origin: 'TRIPULACION', title: 'Revisar filtro', kind: 'NAVE' }),
    ])

    expect(within(screen.getByRole('listitem', { name: /Ejercicio/ })).getByText('Tierra')).toBeVisible()
    expect(
      within(screen.getByRole('listitem', { name: /Revisar filtro/ })).getByText('Tripulación'),
    ).toBeVisible()
  })

  it('filters by kind', async () => {
    renderList([
      task({ id: 'a', title: 'Rutina de salud' }),
      task({ id: 'b', kind: 'NAVE', title: 'Cambiar filtro' }),
    ])

    await userEvent.click(screen.getByRole('button', { name: 'Nave' }))

    expect(screen.queryByText('Rutina de salud')).not.toBeInTheDocument()
    expect(screen.getByText('Cambiar filtro')).toBeVisible()
  })

  it('offers the four filters and starts on "Todas"', () => {
    renderList([task()])

    expect(screen.getByRole('button', { name: 'Todas' })).toHaveAttribute('aria-pressed', 'true')
    for (const name of ['Salud', 'Nave', 'Incidentes']) {
      expect(screen.getByRole('button', { name })).toBeVisible()
    }
  })

  it('does not offer edit or delete on a task from Earth', () => {
    renderList([task({ origin: 'TIERRA' })])

    expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Completar' })).toBeVisible()
  })

  it('offers edit and delete on the crew own task and reports the deletion', async () => {
    const { onDelete } = renderList([task({ id: 'own', origin: 'TRIPULACION' })])

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))

    expect(onDelete).toHaveBeenCalledWith('own')
    expect(screen.getByRole('button', { name: 'Editar' })).toBeVisible()
  })

  it('edits the title of its own task', async () => {
    const { onUpdate } = renderList([task({ id: 'own', origin: 'TRIPULACION', title: 'Antes' })])

    await userEvent.click(screen.getByRole('button', { name: 'Editar' }))
    const input = screen.getByLabelText('Título')
    await userEvent.clear(input)
    await userEvent.type(input, 'Después')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(onUpdate).toHaveBeenCalledWith('own', { title: 'Después', zoneId: null })
  })

  it('asks "¿Funcionó?" when completing and reports the answer', async () => {
    const { onComplete } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Completar' }))
    expect(screen.getByText('¿Funcionó?')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Sí' }))

    expect(onComplete).toHaveBeenCalledWith('a', true)
  })

  it('lets the crew say it does not know whether it worked', async () => {
    const { onComplete } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Completar' }))
    await userEvent.click(screen.getByRole('button', { name: 'No sé' }))

    expect(onComplete).toHaveBeenCalledWith('a', null)
  })

  it('requires a reason to block a task', async () => {
    const { onBlock } = renderList([task({ id: 'a', origin: 'TIERRA' })])

    await userEvent.click(screen.getByRole('button', { name: 'No puedo cumplirla' }))
    expect(screen.getByRole('button', { name: 'Confirmar bloqueo' })).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Motivo'), 'Falta el equipo')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar bloqueo' }))

    expect(onBlock).toHaveBeenCalledWith('a', 'Falta el equipo')
  })

  it('postpones the reminder', async () => {
    const { onSnooze } = renderList([task({ id: 'a' })])

    await userEvent.click(screen.getByRole('button', { name: 'Posponer 30 min' }))

    expect(onSnooze).toHaveBeenCalledWith('a', 30)
  })

  it('keeps a blocked task visible with its reason and no more actions', () => {
    renderList([task({ status: 'BLOQUEADA', blockedReason: 'Falta el equipo' })])

    expect(screen.getByText(/Falta el equipo/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Completar' })).not.toBeInTheDocument()
  })

  it('shows whether a completed measure worked', () => {
    renderList([
      task({ id: 'a', status: 'COMPLETADA', effective: true }),
      task({ id: 'b', status: 'COMPLETADA', effective: false, title: 'Otra' }),
    ])

    expect(screen.getByText('Funcionó')).toBeVisible()
    expect(screen.getByText('No funcionó')).toBeVisible()
  })

  it('shows the streak and says what does not count', () => {
    renderList([
      task({ id: 'a', status: 'COMPLETADA' }),
      task({ id: 'b', status: 'COMPLETADA', origin: 'TIERRA', title: 'De Tierra' }),
      task({ id: 'c', status: 'COMPLETADA', sourceAlertId: 'x', title: 'De alerta' }),
    ])

    expect(screen.getByText('Racha: 1')).toBeVisible()
    expect(screen.getByText(/Las alertas críticas no suman puntos/)).toBeVisible()
  })
})
