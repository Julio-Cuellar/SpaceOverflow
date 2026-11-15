import { canDelete, canEdit, type Task, type TaskKind } from '../features/tasks/model'

const MINUTE_MS = 60_000

function change(tasks: readonly Task[], id: string, apply: (task: Task) => Task): Task[] {
  return tasks.map((task) => (task.id === id ? apply(task) : task))
}

/** Completes a task (of any origin) and records whether the measure worked. */
export function completeTask(tasks: readonly Task[], id: string, effective: boolean | null): Task[] {
  return change(tasks, id, (task) => ({ ...task, status: 'COMPLETED', effective }))
}

/** "I cannot do it": requires a reason and does not delete the task. */
export function blockTask(tasks: readonly Task[], id: string, reason: string): Task[] {
  const trimmed = reason.trim()
  if (trimmed === '') return [...tasks]
  return change(tasks, id, (task) => ({ ...task, status: 'BLOCKED', blockedReason: trimmed }))
}

export function snoozeTask(tasks: readonly Task[], id: string, minutes: number): Task[] {
  return change(tasks, id, (task) => ({
    ...task,
    dueAt: new Date(new Date(task.dueAt).getTime() + minutes * MINUTE_MS).toISOString(),
  }))
}

export interface NewCrewTask {
  kind: Extract<TaskKind, 'HEALTH' | 'SHIP'>
  title: string
  zoneId: string | null
}

/** The crew creates health or ship tasks, also without a link. Incident tasks are opened by the system. */
export function addCrewTask(
  tasks: readonly Task[],
  draft: NewCrewTask,
  id: string,
  dueAt = '2026-11-14T18:00:00Z',
): Task[] {
  const title = draft.title.trim()
  if (title === '') return [...tasks]
  return [
    ...tasks,
    {
      id,
      kind: draft.kind,
      origin: 'CREW',
      title,
      zoneId: draft.zoneId,
      status: 'PENDING',
      dueAt,
      blockedReason: null,
      effective: null,
      sourceAlertId: null,
    },
  ]
}

export function updateCrewTask(
  tasks: readonly Task[],
  id: string,
  changes: { title: string; zoneId: string | null },
): Task[] {
  return change(tasks, id, (task) =>
    canEdit(task) ? { ...task, title: changes.title.trim() || task.title, zoneId: changes.zoneId } : task,
  )
}

export function deleteCrewTask(tasks: readonly Task[], id: string): Task[] {
  return tasks.filter((task) => task.id !== id || !canDelete(task))
}
