import { useId, useState } from 'react'
import type { IncidentTypeView } from '../../data/mocks/incidentTypes'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { SevPill } from '../../shared/ui/SevPill'

interface CatalogListProps {
  types: IncidentTypeView[]
  /** Pre-fills the report form with the chosen type. */
  onReport: (typeKey: string) => void
}

const DETECTION_LABEL: Record<IncidentTypeView['detection'], string> = {
  AUTO: 'AUTO',
  MANUAL: 'MANUAL',
}

/** Catalog of incident types, filterable by category. */
export function CatalogList({ types, onReport }: CatalogListProps) {
  const categoryId = useId()
  const categories = [...new Set(types.map((t) => t.category))]
  const [category, setCategory] = useState('')

  const visible = category === '' ? types : types.filter((t) => t.category === category)

  return (
    <section aria-label="Incident catalog">
      <label htmlFor={categoryId}>Category</label>
      <select id={categoryId} value={category} onChange={(e) => setCategory(e.target.value)}>
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <p>{visible.length} types</p>

      <ul>
        {visible.map((type) => (
          <li key={type.key}>
            <strong>{type.name}</strong> <span>{DETECTION_LABEL[type.detection]}</span>{' '}
            <SevPill level={type.defaultSeverity} /> <EvidenceBadge state={type.evidenceState} />
            <p>Typical zones: {type.typicalZones.join(', ')}</p>
            <button type="button" onClick={() => onReport(type.key)}>
              Report
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
