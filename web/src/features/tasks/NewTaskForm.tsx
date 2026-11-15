import { useId, useState } from 'react'
import type { NewCrewTask } from '../../app/tasks'

interface NewTaskFormProps {
  zones: { id: string; name: string }[]
  onCreate: (draft: NewCrewTask) => void
}

/** Tarea propia: funciona sin enlace con Tierra. Los incidentes los abre el sistema, no la tripulación. */
export function NewTaskForm({ zones, onCreate }: NewTaskFormProps) {
  const ids = { kind: useId(), zone: useId(), title: useId() }
  const [kind, setKind] = useState<NewCrewTask['kind']>('SALUD')
  const [zoneId, setZoneId] = useState('')
  const [title, setTitle] = useState('')

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onCreate({ kind, title, zoneId: zoneId === '' ? null : zoneId })
        setTitle('')
      }}
    >
      <label htmlFor={ids.kind}>Tipo</label>
      <select
        id={ids.kind}
        value={kind}
        onChange={(event) => setKind(event.target.value as NewCrewTask['kind'])}
      >
        <option value="SALUD">Salud</option>
        <option value="NAVE">Nave</option>
      </select>

      <label htmlFor={ids.zone}>Zona</label>
      <select id={ids.zone} value={zoneId} onChange={(event) => setZoneId(event.target.value)}>
        <option value="">Sin zona</option>
        {zones.map((zone) => (
          <option key={zone.id} value={zone.id}>
            {zone.name}
          </option>
        ))}
      </select>

      <label htmlFor={ids.title}>Título</label>
      <input
        id={ids.title}
        type="text"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />

      <button type="submit" disabled={title.trim() === ''}>
        Crear tarea
      </button>
    </form>
  )
}
