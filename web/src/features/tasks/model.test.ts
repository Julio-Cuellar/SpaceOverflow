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

describe('filterTasks', () => {
  const tasks = [
    task({ id: 'a', kind: 'SALUD' }),
    task({ id: 'b', kind: 'NAVE' }),
    task({ id: 'c', kind: 'INCIDENTE' }),
  ]

  it('returns every task for "TODAS"', () => {
    expect(filterTasks(tasks, 'TODAS').map((t) => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('keeps only the chosen kind', () => {
    expect(filterTasks(tasks, 'NAVE').map((t) => t.id)).toEqual(['b'])
  })
})

describe('who can change a task', () => {
  it('lets the crew edit and delete only its own tasks', () => {
    expect(canEdit(task({ origin: 'TRIPULACION' }))).toBe(true)
    expect(canDelete(task({ origin: 'TRIPULACION' }))).toBe(true)
  })

  it('never lets the crew edit or delete a task from Earth or the system', () => {
    for (const origin of ['TIERRA', 'SISTEMA'] as const) {
      expect(canEdit(task({ origin }))).toBe(false)
      expect(canDelete(task({ origin }))).toBe(false)
    }
  })
})

describe('streak and achievements', () => {
  it('counts a completed health routine', () => {
    expect(countsForStreak(task({ status: 'COMPLETADA' }))).toBe(true)
  })

  it('does not count a pending or blocked task', () => {
    expect(countsForStreak(task({ status: 'PENDIENTE' }))).toBe(false)
    expect(countsForStreak(task({ status: 'BLOQUEADA' }))).toBe(false)
  })

  it('does not count ship maintenance or incident tasks', () => {
    expect(countsForStreak(task({ kind: 'NAVE', status: 'COMPLETADA' }))).toBe(false)
    expect(countsForStreak(task({ kind: 'INCIDENTE', status: 'COMPLETADA' }))).toBe(false)
  })

  it('does not count tasks assigned by Earth', () => {
    expect(countsForStreak(task({ origin: 'TIERRA', status: 'COMPLETADA' }))).toBe(false)
  })

  it('never gamifies the response to an alert', () => {
    expect(countsForStreak(task({ status: 'COMPLETADA', sourceAlertId: 'alert-1' }))).toBe(false)
  })

  it('adds up only what counts', () => {
    const tasks = [
      task({ id: 'a', status: 'COMPLETADA' }),
      task({ id: 'b', status: 'COMPLETADA', origin: 'TRIPULACION' }),
      task({ id: 'c', status: 'COMPLETADA', origin: 'TIERRA' }),
      task({ id: 'd', status: 'COMPLETADA', sourceAlertId: 'alert-1' }),
      task({ id: 'e', status: 'PENDIENTE' }),
    ]

    expect(streakOf(tasks)).toBe(2)
  })
})

describe('originLabel', () => {
  it('names each origin for the card tag', () => {
    expect(originLabel('TIERRA')).toBe('Tierra')
    expect(originLabel('SISTEMA')).toBe('Sistema')
    expect(originLabel('TRIPULACION')).toBe('Tripulación')
  })
})
