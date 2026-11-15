export type TaskKind = 'SALUD' | 'NAVE' | 'INCIDENTE'
export type TaskOrigin = 'TIERRA' | 'SISTEMA' | 'TRIPULACION'
export type TaskStatus = 'PENDIENTE' | 'COMPLETADA' | 'BLOQUEADA'
export type TaskFilter = 'TODAS' | TaskKind

/** Tarea del día (plan, G8). Las de Tierra y las de incidente nunca las crea la tripulación. */
export interface Task {
  id: string
  kind: TaskKind
  origin: TaskOrigin
  title: string
  zoneId: string | null
  status: TaskStatus
  dueAt: string
  /** Motivo de «No puedo cumplirla». La tarea no se borra. */
  blockedReason: string | null
  /** «¿Funcionó?» al completar. `null` si no se sabe o aún no se completó. */
  effective: boolean | null
  /** Si nació de una alerta: la respuesta a una alerta no se gamifica. */
  sourceAlertId: string | null
}

export function filterTasks(tasks: readonly Task[], filter: TaskFilter): Task[] {
  return filter === 'TODAS' ? [...tasks] : tasks.filter((t) => t.kind === filter)
}

/** Una tarea de Tierra o del sistema no se edita ni se borra: solo se completa, pospone o bloquea. */
export function canEdit(task: Task): boolean {
  return task.origin === 'TRIPULACION'
}

export function canDelete(task: Task): boolean {
  return task.origin === 'TRIPULACION'
}

/** Solo las rutinas de salud completadas suman. Ni Tierra, ni incidentes, ni alertas (plan, 13.8). */
export function countsForStreak(task: Task): boolean {
  return (
    task.status === 'COMPLETADA' &&
    task.kind === 'SALUD' &&
    task.origin !== 'TIERRA' &&
    task.sourceAlertId === null
  )
}

export function streakOf(tasks: readonly Task[]): number {
  return tasks.filter(countsForStreak).length
}

const ORIGIN_LABELS: Record<TaskOrigin, string> = {
  TIERRA: 'Tierra',
  SISTEMA: 'Sistema',
  TRIPULACION: 'Tripulación',
}

export function originLabel(origin: TaskOrigin): string {
  return ORIGIN_LABELS[origin]
}

const KIND_LABELS: Record<TaskKind, string> = {
  SALUD: 'Salud',
  NAVE: 'Nave',
  INCIDENTE: 'Incidentes',
}

export function kindLabel(kind: TaskKind): string {
  return KIND_LABELS[kind]
}
