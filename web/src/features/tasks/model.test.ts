import { describe, expect, it } from 'vitest'
import {
  canDelete,
  canEdit,
  countsForStreak,
  filterTasks,
  originLabel,
  streakOf,
  type Task,
} from './model'

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

describe('filterTasks', () => {
  const tasks = [
    task({ id: 'a', kind: 'HEALTH' }),
    task({ id: 'b', kind: 'SHIP' }),
    task({ id: 'c', kind: 'INCIDENT' }),
  ]

  it('returns every task for "TODAS"', () => {
    expect(filterTasks(tasks, 'TODAS').map((t) => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('keeps only the chosen kind', () => {
    expect(filterTasks(tasks, 'SHIP').map((t) => t.id)).toEqual(['b'])
  })
})

describe('who can change a task', () => {
  it('lets the crew edit and delete only its own tasks', () => {
    expect(canEdit(task({ origin: 'CREW' }))).toBe(true)
    expect(canDelete(task({ origin: 'CREW' }))).toBe(true)
  })

  it('never lets the crew edit or delete a task from Earth or the system', () => {
    for (const origin of ['GROUND', 'SYSTEM'] as const) {
      expect(canEdit(task({ origin }))).toBe(false)
      expect(canDelete(task({ origin }))).toBe(false)
    }
  })
})

describe('streak and achievements', () => {
  it('counts a completed health routine', () => {
    expect(countsForStreak(task({ status: 'COMPLETED' }))).toBe(true)
  })

  it('does not count a pending or blocked task', () => {
    expect(countsForStreak(task({ status: 'PENDING' }))).toBe(false)
    expect(countsForStreak(task({ status: 'BLOCKED' }))).toBe(false)
  })

  it('does not count ship maintenance or incident tasks', () => {
    expect(countsForStreak(task({ kind: 'SHIP', status: 'COMPLETED' }))).toBe(false)
    expect(countsForStreak(task({ kind: 'INCIDENT', status: 'COMPLETED' }))).toBe(false)
  })

  it('does not count tasks assigned by Earth', () => {
    expect(countsForStreak(task({ origin: 'GROUND', status: 'COMPLETED' }))).toBe(false)
  })

  it('never gamifies the response to an alert', () => {
    expect(countsForStreak(task({ status: 'COMPLETED', sourceAlertId: 'alert-1' }))).toBe(false)
  })

  it('adds up only what counts', () => {
    const tasks = [
      task({ id: 'a', status: 'COMPLETED' }),
      task({ id: 'b', status: 'COMPLETED', origin: 'CREW' }),
      task({ id: 'c', status: 'COMPLETED', origin: 'GROUND' }),
      task({ id: 'd', status: 'COMPLETED', sourceAlertId: 'alert-1' }),
      task({ id: 'e', status: 'PENDING' }),
    ]

    expect(streakOf(tasks)).toBe(2)
  })
})

describe('originLabel', () => {
  it('names each origin for the card tag', () => {
    expect(originLabel('GROUND')).toBe('Ground')
    expect(originLabel('SYSTEM')).toBe('System')
    expect(originLabel('CREW')).toBe('Crew')
  })
})
