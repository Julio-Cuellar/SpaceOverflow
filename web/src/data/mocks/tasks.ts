import type { Task } from '../../features/tasks/model'

/**
 * Tareas de demostración (datos simulados, no de NASA). Se retiran cuando la interfaz consuma
 * `tasks(kind, status)` y `task.assigned` por WS (hito I5 de Dev A).
 */
export const tasksFixture: Task[] = [
  {
    id: 'task-presion',
    kind: 'SALUD',
    origin: 'SISTEMA',
    title: 'Medir la presión arterial',
    zoneId: null,
    status: 'PENDIENTE',
    dueAt: '2026-11-14T12:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-ejercicio',
    kind: 'SALUD',
    origin: 'TIERRA',
    title: 'Ejercicio de 30 minutos',
    zoneId: null,
    status: 'PENDIENTE',
    dueAt: '2026-11-14T14:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-filtro',
    kind: 'NAVE',
    origin: 'SISTEMA',
    title: 'Revisar los filtros de CO₂',
    zoneId: 'z-lab',
    status: 'PENDIENTE',
    dueAt: '2026-11-14T16:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
  {
    id: 'task-sellos',
    kind: 'INCIDENTE',
    origin: 'SISTEMA',
    title: 'Inspeccionar los sellos de la esclusa',
    zoneId: 'z-esclusa',
    status: 'PENDIENTE',
    dueAt: '2026-11-14T13:00:00Z',
    blockedReason: null,
    effective: null,
    sourceAlertId: null,
  },
]
