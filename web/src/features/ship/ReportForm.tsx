import { useId, useState } from 'react'
import type { IncidentTypeView } from '../../data/mocks/incidentTypes'
import { SEVERITIES, type Severity, severityMeta } from '../../shared/lib/severity'

export interface ReportPayload {
  typeKey: string
  zoneId: string
  severity: Severity
  title: string
  description: string
}

interface ReportFormProps {
  types: IncidentTypeView[]
  zones: { id: string; name: string }[]
  onReport: (payload: ReportPayload) => void
  /** Type that arrives from the catalog via "Report". To change it, the app remounts the form. */
  presetTypeKey?: string
}

/** Manual report: category, type, zone and the severity proposed by the type. */
export function ReportForm({ types, zones, onReport, presetTypeKey }: ReportFormProps) {
  const ids = {
    category: useId(),
    type: useId(),
    zone: useId(),
    severity: useId(),
    title: useId(),
    description: useId(),
  }
  const categories = [...new Set(types.map((t) => t.category))]

  const preset = types.find((t) => t.key === presetTypeKey)
  const [category, setCategory] = useState(preset?.category ?? '')
  const [typeKey, setTypeKey] = useState(preset?.key ?? '')
  const [zoneId, setZoneId] = useState('')
  const [severity, setSeverity] = useState<Severity | ''>(preset?.defaultSeverity ?? '')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  const typesInCategory = types.filter((t) => t.category === category)
  const chosen = types.find((t) => t.key === typeKey)
  const canSend = chosen !== undefined && zoneId !== '' && severity !== ''

  const pickCategory = (value: string) => {
    setCategory(value)
    setTypeKey('')
    setSeverity('')
  }

  const pickType = (key: string) => {
    setTypeKey(key)
    setSeverity(types.find((t) => t.key === key)?.defaultSeverity ?? '')
  }

  const submit = () => {
    if (!chosen || severity === '') return
    onReport({
      typeKey: chosen.key,
      zoneId,
      severity,
      title: title.trim() || chosen.name,
      description,
    })
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <label htmlFor={ids.category}>Category</label>
      <select id={ids.category} value={category} onChange={(e) => pickCategory(e.target.value)}>
        <option value="">Choose category</option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <label htmlFor={ids.type}>Type</label>
      <select
        id={ids.type}
        value={typeKey}
        disabled={category === ''}
        onChange={(e) => pickType(e.target.value)}
      >
        <option value="">Choose type</option>
        {typesInCategory.map((t) => (
          <option key={t.key} value={t.key}>
            {t.name}
          </option>
        ))}
      </select>

      <label htmlFor={ids.zone}>Zone</label>
      <select id={ids.zone} value={zoneId} onChange={(e) => setZoneId(e.target.value)}>
        <option value="">Choose zone</option>
        {zones.map((z) => (
          <option key={z.id} value={z.id}>
            {z.name}
          </option>
        ))}
      </select>

      <label htmlFor={ids.severity}>Severity</label>
      <select
        id={ids.severity}
        value={severity}
        onChange={(e) => setSeverity(e.target.value as Severity)}
      >
        <option value="">Choose severity</option>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {severityMeta(s).label}
          </option>
        ))}
      </select>

      <label htmlFor={ids.title}>Title</label>
      <input
        id={ids.title}
        type="text"
        value={title}
        placeholder={chosen?.name ?? ''}
        onChange={(e) => setTitle(e.target.value)}
      />

      <label htmlFor={ids.description}>Description</label>
      <textarea
        id={ids.description}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />

      <button type="submit" disabled={!canSend}>
        Submit report
      </button>
    </form>
  )
}
