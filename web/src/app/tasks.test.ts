import { describe, expect, it } from 'vitest'
import type { Task } from '../features/tasks/model'
import {
  addCrewTask,
  blockTask,
  completeTask,
  deleteCrewTask,
  snoozeTask,
  updateCrewTask,
} from './tasks'

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    kind: 'SALUD',
    origin: 'TIERRA',
    title: 'Ejercicio de 30 minutos',
    zoneId: null,
    status: 'PENDIENTE',
    dueAt: '2026-11-14T12:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
    ...overrides,
  }
}

describe('completeTask', () => {
  it('marks the task as completed and records whether it worked', () => {
    const [done] = completeTask([task()], 't1', true)

    expect(done?.status).toBe('COMPLETADA')
    expect(done?.effective).toBe(true)
  })

  it('accepts "no sé": effectiveness stays unknown', () => {
    const [done] = completeTask([task()], 't1', null)

    expect(done?.status).toBe('COMPLETADA')
    expect(done?.effective).toBeNull()
  })

  it('also lets the crew complete a task from Earth', () => {
    const [done] = completeTask([task({ origin: 'TIERRA' })], 't1', true)

    expect(done?.status).toBe('COMPLETADA')
  })
})

describe('blockTask', () => {
  it('keeps the task and stores the reason', () => {
    const [blocked] = blockTask([task()], 't1', 'Falta el equipo')

    expect(blocked?.status).toBe('BLOQUEADA')
    expect(blocked?.blockedReason).toBe('Falta el equipo')
  })

  it('does nothing without a reason', () => {
    const tasks = [task()]

    expect(blockTask(tasks, 't1', '   ')).toEqual(tasks)
  })

  it('does not delete anything', () => {
    expect(blockTask([task(), task({ id: 't2' })], 't1', 'x')).toHaveLength(2)
  })
})

describe('snoozeTask', () => {
  it('moves the reminder forward by the given minutes', () => {
    const [later] = snoozeTask([task({ dueAt: '2026-11-14T12:00:00Z' })], 't1', 30)

    expect(later?.dueAt).toBe('2026-11-14T12:30:00.000Z')
  })
})

describe('crew tasks', () => {
  it('creates a task with origin TRIPULACION and no link needed', () => {
    const tasks = addCrewTask([], { kind: 'NAVE', title: 'Revisar el filtro', zoneId: 'z-lab' }, 't9')

    expect(tasks).toEqual([
      expect.objectContaining({
        id: 't9',
        kind: 'NAVE',
        origin: 'TRIPULACION',
        status: 'PENDIENTE',
        title: 'Revisar el filtro',
        zoneId: 'z-lab',
      }),
    ])
  })

  it('does not create a task with an empty title', () => {
    expect(addCrewTask([], { kind: 'SALUD', title: '  ', zoneId: null }, 't9')).toEqual([])
  })

  it('edits only the title and zone of its own task', () => {
    const own = task({ id: 'own', origin: 'TRIPULACION' })

    const [edited] = updateCrewTask([own], 'own', { title: 'Nuevo', zoneId: 'z-lab' })

    expect(edited?.title).toBe('Nuevo')
    expect(edited?.zoneId).toBe('z-lab')
  })

  it('refuses to edit a task from Earth', () => {
    const fromEarth = task({ origin: 'TIERRA' })

    expect(updateCrewTask([fromEarth], 't1', { title: 'Otro', zoneId: null })).toEqual([fromEarth])
  })

  it('deletes its own task', () => {
    expect(deleteCrewTask([task({ origin: 'TRIPULACION' })], 't1')).toEqual([])
  })

  it('refuses to delete a task from Earth or the system', () => {
    const tasks = [task({ origin: 'TIERRA' }), task({ id: 't2', origin: 'SISTEMA' })]

    expect(deleteCrewTask(tasks, 't1')).toEqual(tasks)
    expect(deleteCrewTask(tasks, 't2')).toEqual(tasks)
  })
})
