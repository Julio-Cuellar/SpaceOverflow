import { type Severity, severityMeta } from '../../shared/lib/severity'

export interface ZoneLayout {
  x: number
  y: number
  w: number
  h: number
}

/** Physical zone of the ship. The floor plan comes from `layout` (data, not code). */
export interface Zone {
  id: string
  name: string
  layout: ZoneLayout
  status: Severity
}

export type TicketStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'

export interface Ticket {
  id: string
  code: string
  title: string
  severity: Severity
  status: TicketStatus
  zoneId: string
  /** ALERT: opened by a rule. MANUAL: reported by the crew. */
  source: 'ALERT' | 'MANUAL'
  openedAt: string
  /** Whether the values that opened the ticket are back in range. */
  valuesInRange: boolean
}

/** Order: highest severity first, and within each level the oldest. Resolved last. */
export function sortTickets(tickets: readonly Ticket[]): Ticket[] {
  return [...tickets].sort((a, b) => {
    const aResolved = a.status === 'RESOLVED' ? 1 : 0
    const bResolved = b.status === 'RESOLVED' ? 1 : 0
    if (aResolved !== bResolved) return aResolved - bResolved

    const bySeverity = severityMeta(b.severity).rank - severityMeta(a.severity).rank
    if (bySeverity !== 0) return bySeverity

    return a.openedAt.localeCompare(b.openedAt)
  })
}

/** An automatic ticket cannot be resolved while its values are still out of range. */
export function canResolve(ticket: Ticket): boolean {
  return ticket.source !== 'ALERT' || ticket.valuesInRange
}
