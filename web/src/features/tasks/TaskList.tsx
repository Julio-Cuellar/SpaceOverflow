import { useId, useState } from 'react'
import {
  canDelete,
  canEdit,
  filterTasks,
  kindLabel,
  originLabel,
  streakOf,
  type Task,
  type TaskFilter,
} from './model'

const FILTERS: { value: TaskFilter; label: string }[] = [
  { value: 'TODAS', label: 'Todas' },
  { value: 'SALUD', label: 'Salud' },
  { value: 'NAVE', label: 'Nave' },
  { value: 'INCIDENTE', label: 'Incidentes' },
]

const SNOOZE_MINUTES = 30

interface TaskListProps {
  tasks: Task[]
  zones: { id: string; name: string }[]
  onComplete: (id: string, effective: boolean | null) => void
  onBlock: (id: string, reason: string) => void
  onSnooze: (id: string, minutes: number) => void
  onUpdate: (id: string, changes: { title: string; zoneId: string | null }) => void
  onDelete: (id: string) => void
}

/** Tareas del día con filtros, etiqueta de origen y las acciones que permite cada origen (plan, F10). */
export function TaskList({ tasks, zones, ...handlers }: TaskListProps) {
  const [filter, setFilter] = useState<TaskFilter>('TODAS')
  const visible = filterTasks(tasks, filter)

  return (
    <section aria-label="Tareas del día">
      <p>
        <strong>Racha: {streakOf(tasks)}</strong>
      </p>
      <p>
        Solo las rutinas de salud suman a la racha. Las alertas críticas no suman puntos, ni las
        tareas de Tierra ni los incidentes.
      </p>

      <div role="group" aria-label="Filtro de tareas">
        {FILTERS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <ul>
        {visible.map((task) => (
          <TaskCard key={task.id} task={task} zones={zones} {...handlers} />
        ))}
      </ul>
    </section>
  )
}

type Mode = 'idle' | 'complete' | 'block' | 'edit'

function TaskCard({
  task,
  zones,
  onComplete,
  onBlock,
  onSnooze,
  onUpdate,
  onDelete,
}: { task: Task } & Omit<TaskListProps, 'tasks'>) {
  const [mode, setMode] = useState<Mode>('idle')
  const [reason, setReason] = useState('')
  const [title, setTitle] = useState(task.title)
  const [zoneId, setZoneId] = useState(task.zoneId ?? '')
  const ids = { reason: useId(), title: useId(), zone: useId() }
  const open = task.status === 'PENDIENTE'

  return (
    <li aria-label={task.title}>
      <strong>{task.title}</strong> <span>{originLabel(task.origin)}</span>{' '}
      <span>{kindLabel(task.kind)}</span>{' '}
      <time dateTime={task.dueAt}>
        {new Date(task.dueAt).toLocaleTimeString('es', {
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'UTC',
        })}{' '}
        UTC
      </time>

      {task.status === 'COMPLETADA' && (
        <p>
          Completada
          {task.effective === true && <> · <span>Funcionó</span></>}
          {task.effective === false && <> · <span>No funcionó</span></>}
        </p>
      )}
      {task.status === 'BLOQUEADA' && <p>No se puede cumplir: {task.blockedReason}</p>}

      {open && mode === 'idle' && (
        <div>
          <button type="button" onClick={() => setMode('complete')}>
            Completar
          </button>
          <button type="button" onClick={() => onSnooze(task.id, SNOOZE_MINUTES)}>
            Posponer {SNOOZE_MINUTES} min
          </button>
          <button type="button" onClick={() => setMode('block')}>
            No puedo cumplirla
          </button>
          {canEdit(task) && (
            <button type="button" onClick={() => setMode('edit')}>
              Editar
            </button>
          )}
          {canDelete(task) && (
            <button type="button" onClick={() => onDelete(task.id)}>
              Eliminar
            </button>
          )}
        </div>
      )}

      {open && mode === 'complete' && (
        <div>
          <span>¿Funcionó?</span>
          <button type="button" onClick={() => onComplete(task.id, true)}>
            Sí
          </button>
          <button type="button" onClick={() => onComplete(task.id, false)}>
            No
          </button>
          <button type="button" onClick={() => onComplete(task.id, null)}>
            No sé
          </button>
        </div>
      )}

      {open && mode === 'block' && (
        <div>
          <label htmlFor={ids.reason}>Motivo</label>
          <input
            id={ids.reason}
            type="text"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <button
            type="button"
            disabled={reason.trim() === ''}
            onClick={() => onBlock(task.id, reason)}
          >
            Confirmar bloqueo
          </button>
        </div>
      )}

      {open && mode === 'edit' && (
        <div>
          <label htmlFor={ids.title}>Título</label>
          <input
            id={ids.title}
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <label htmlFor={ids.zone}>Zona</label>
          <select id={ids.zone} value={zoneId} onChange={(event) => setZoneId(event.target.value)}>
            <option value="">Sin zona</option>
            {zones.map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              onUpdate(task.id, { title, zoneId: zoneId === '' ? null : zoneId })
              setMode('idle')
            }}
          >
            Guardar
          </button>
        </div>
      )}
    </li>
  )
}
