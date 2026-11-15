import type { Task } from '../../features/tasks/model'

/**
 * Demo tasks (simulated data, not from NASA). They are removed when the interface consumes
 * `tasks(kind, status)` and `task.assigned` over WS (milestone I5 of Dev A).
 */
export const tasksFixture: Task[] = [
  {
    id: 'task-presion',
    kind: 'HEALTH',
    origin: 'SYSTEM',
    title: 'Measure blood pressure',
    zoneId: null,
    status: 'PENDING',
    dueAt: '2026-11-14T12:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-ejercicio',
    kind: 'HEALTH',
    origin: 'GROUND',
    title: '30-minute exercise',
    zoneId: null,
    status: 'PENDING',
    dueAt: '2026-11-14T14:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-filtro',
    kind: 'SHIP',
    origin: 'SYSTEM',
    title: 'Check the CO₂ filters',
    zoneId: 'z-lab',
    status: 'PENDING',
    dueAt: '2026-11-14T16:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-sellos',
    kind: 'INCIDENT',
    origin: 'SYSTEM',
    title: 'Inspeccionar los sellos de la esclusa',
    zoneId: 'z-esclusa',
    status: 'PENDING',
    dueAt: '2026-11-14T13:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
]
