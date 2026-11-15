import { useId, useState } from 'react'
import type { NewCrewTask } from '../../app/tasks'

interface NewTaskFormProps {
  zones: { id: string; name: string }[]
  onCreate: (draft: NewCrewTask) => void
}

/** The crew's own task: works without a link with Ground. Incidents are opened by the system, not the crew. */
export function NewTaskForm({ zones, onCreate }: NewTaskFormProps) {
  const ids = { kind: useId(), zone: useId(), title: useId() }
  const [kind, setKind] = useState<NewCrewTask['kind']>('HEALTH')
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
      <label htmlFor={ids.kind}>Type</label>
      <select
        id={ids.kind}
        value={kind}
        onChange={(event) => setKind(event.target.value as NewCrewTask['kind'])}
      >
        <option value="HEALTH">Health</option>
        <option value="SHIP">Ship</option>
      </select>

      <label htmlFor={ids.zone}>Zone</label>
      <select id={ids.zone} value={zoneId} onChange={(event) => setZoneId(event.target.value)}>
        <option value="">Sin zona</option>
        {zones.map((zone) => (
          <option key={zone.id} value={zone.id}>
            {zone.name}
          </option>
        ))}
      </select>

      <label htmlFor={ids.title}>Title</label>
      <input
        id={ids.title}
        type="text"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />

      <button type="submit" disabled={title.trim() === ''}>
        Create task
      </button>
    </form>
  )
}
