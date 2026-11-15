import { type Severity, severityMeta } from '../../shared/lib/severity'

export interface ZoneLayout {
  x: number
  y: number
  w: number
  h: number
}

/** Zona física de la nave. El plano sale de `layout` (dato, no código). */
export interface Zone {
  id: string
  name: string
  layout: ZoneLayout
  status: Severity
}

export type TicketStatus = 'ABIERTO' | 'RECONOCIDO' | 'RESUELTO'

export interface Ticket {
  id: string
  code: string
  title: string
  severity: Severity
  status: TicketStatus
  zoneId: string
  /** ALERTA: abierto por una regla. MANUAL: reportado por la tripulación. */
  source: 'ALERTA' | 'MANUAL'
  openedAt: string
  /** Si los valores que abrieron el ticket vuelven a estar en rango. */
  valuesInRange: boolean
}

/** Orden: severidad más alta primero, y dentro de cada nivel el más antiguo. Resueltos al final. */
export function sortTickets(tickets: readonly Ticket[]): Ticket[] {
  return [...tickets].sort((a, b) => {
    const aResolved = a.status === 'RESUELTO' ? 1 : 0
    const bResolved = b.status === 'RESUELTO' ? 1 : 0
    if (aResolved !== bResolved) return aResolved - bResolved

    const bySeverity = severityMeta(b.severity).rank - severityMeta(a.severity).rank
    if (bySeverity !== 0) return bySeverity

    return a.openedAt.localeCompare(b.openedAt)
  })
}

/** Un ticket automático no se resuelve mientras sus valores sigan fuera de rango. */
export function canResolve(ticket: Ticket): boolean {
  return ticket.source !== 'ALERTA' || ticket.valuesInRange
}
