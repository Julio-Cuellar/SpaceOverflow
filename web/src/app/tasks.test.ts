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
    kind: 'HEALTH',
    origin: 'GROUND',
    title: '30-minute exercise',
    zoneId: null,
    status: 'PENDING',
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

    expect(done?.status).toBe('COMPLETED')
    expect(done?.effective).toBe(true)
  })

  it('accepts "not sure": effectiveness stays unknown', () => {
    const [done] = completeTask([task()], 't1', null)

    expect(done?.status).toBe('COMPLETED')
    expect(done?.effective).toBeNull()
  })

  it('also lets the crew complete a task from Earth', () => {
    const [done] = completeTask([task({ origin: 'GROUND' })], 't1', true)

    expect(done?.status).toBe('COMPLETED')
  })
})

describe('blockTask', () => {
  it('keeps the task and stores the reason', () => {
    const [blocked] = blockTask([task()], 't1', 'Missing equipment')

    expect(blocked?.status).toBe('BLOCKED')
    expect(blocked?.blockedReason).toBe('Missing equipment')
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
  it('creates a task with origin CREW and no link needed', () => {
    const tasks = addCrewTask([], { kind: 'SHIP', title: 'Check the filter', zoneId: 'z-lab' }, 't9')

    expect(tasks).toEqual([
      expect.objectContaining({
        id: 't9',
        kind: 'SHIP',
        origin: 'CREW',
        status: 'PENDING',
        title: 'Check the filter',
        zoneId: 'z-lab',
      }),
    ])
  })

  it('does not create a task with an empty title', () => {
    expect(addCrewTask([], { kind: 'HEALTH', title: '  ', zoneId: null }, 't9')).toEqual([])
  })

  it('edits only the title and zone of its own task', () => {
    const own = task({ id: 'own', origin: 'CREW' })

    const [edited] = updateCrewTask([own], 'own', { title: 'Nuevo', zoneId: 'z-lab' })

    expect(edited?.title).toBe('Nuevo')
    expect(edited?.zoneId).toBe('z-lab')
  })

  it('refuses to edit a task from Earth', () => {
    const fromEarth = task({ origin: 'GROUND' })

    expect(updateCrewTask([fromEarth], 't1', { title: 'Otro', zoneId: null })).toEqual([fromEarth])
  })

  it('deletes its own task', () => {
    expect(deleteCrewTask([task({ origin: 'CREW' })], 't1')).toEqual([])
  })

  it('refuses to delete a task from Earth or the system', () => {
    const tasks = [task({ origin: 'GROUND' }), task({ id: 't2', origin: 'SYSTEM' })]

    expect(deleteCrewTask(tasks, 't1')).toEqual(tasks)
    expect(deleteCrewTask(tasks, 't2')).toEqual(tasks)
  })
})
