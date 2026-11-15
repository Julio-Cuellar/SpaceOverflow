export type TaskKind = 'HEALTH' | 'SHIP' | 'INCIDENT'
export type TaskOrigin = 'GROUND' | 'SYSTEM' | 'CREW'
export type TaskStatus = 'PENDING' | 'COMPLETED' | 'BLOCKED'
export type TaskFilter = 'TODAS' | TaskKind

/** Task of the day (plan, G8). Ground and incident tasks are never created by the crew. */
export interface Task {
  id: string
  kind: TaskKind
  origin: TaskOrigin
  title: string
  zoneId: string | null
  status: TaskStatus
  dueAt: string
  /** Reason of "I cannot do it". The task is not deleted. */
  blockedReason: string | null
  /** "Did it work?" when completing. `null` if unknown or not completed yet. */
  effective: boolean | null
  /** If it came from an alert: the response to an alert is not gamified. */
  sourceAlertId: string | null
}

export function filterTasks(tasks: readonly Task[], filter: TaskFilter): Task[] {
  return filter === 'TODAS' ? [...tasks] : tasks.filter((t) => t.kind === filter)
}

/** A Ground or system task is not edited or deleted: it can only be completed, snoozed or blocked. */
export function canEdit(task: Task): boolean {
  return task.origin === 'CREW'
}

export function canDelete(task: Task): boolean {
  return task.origin === 'CREW'
}

/** Only completed health routines count. Not Ground, not incidents, not alerts (plan, 13.8). */
export function countsForStreak(task: Task): boolean {
  return (
    task.status === 'COMPLETED' &&
    task.kind === 'HEALTH' &&
    task.origin !== 'GROUND' &&
    task.sourceAlertId === null
  )
}

export function streakOf(tasks: readonly Task[]): number {
  return tasks.filter(countsForStreak).length
}

const ORIGIN_LABELS: Record<TaskOrigin, string> = {
  GROUND: 'Ground',
  SYSTEM: 'System',
  CREW: 'Crew',
}

export function originLabel(origin: TaskOrigin): string {
  return ORIGIN_LABELS[origin]
}

const KIND_LABELS: Record<TaskKind, string> = {
  HEALTH: 'Health',
  SHIP: 'Ship',
  INCIDENT: 'Incidents',
}

export function kindLabel(kind: TaskKind): string {
  return KIND_LABELS[kind]
}
