import { describe, expect, it } from 'vitest'
import { canResolve, sortTickets, type Ticket } from './model'

const ticket = (overrides: Partial<Ticket>): Ticket => ({
  id: 't',
  code: 'INC-0000',
  title: 'Incident',
  severity: 'ATTENTION',
  status: 'OPEN',
  zoneId: 'z-lab',
  source: 'MANUAL',
  openedAt: '2026-11-14T10:00:00Z',
  valuesInRange: true,
  ...overrides,
})

describe('sortTickets', () => {
  it('orders by severity first, then by age (oldest first)', () => {
    const sorted = sortTickets([
      ticket({ id: 'a', severity: 'ATTENTION', openedAt: '2026-11-14T09:00:00Z' }),
      ticket({ id: 'b', severity: 'CRITICAL', openedAt: '2026-11-14T11:00:00Z' }),
      ticket({ id: 'c', severity: 'ATTENTION', openedAt: '2026-11-14T08:00:00Z' }),
    ])

    expect(sorted.map((t) => t.id)).toEqual(['b', 'c', 'a'])
  })

  it('puts resolved tickets last', () => {
    const sorted = sortTickets([
      ticket({ id: 'resolved', severity: 'CRITICAL', status: 'RESOLVED' }),
      ticket({ id: 'open', severity: 'ATTENTION' }),
    ])

    expect(sorted.map((t) => t.id)).toEqual(['open', 'resolved'])
  })
})

describe('canResolve', () => {
  it('blocks resolving an automatic ticket while its values are still out of range', () => {
    expect(canResolve(ticket({ source: 'ALERT', valuesInRange: false }))).toBe(false)
  })

  it('allows resolving an automatic ticket once its values are back in range', () => {
    expect(canResolve(ticket({ source: 'ALERT', valuesInRange: true }))).toBe(true)
  })

  it('always allows resolving a manual ticket, since the crew decides', () => {
    expect(canResolve(ticket({ source: 'MANUAL', valuesInRange: false }))).toBe(true)
  })
})
