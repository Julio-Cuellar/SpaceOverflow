import { useId, useState } from 'react'
import type { IncidentTypeView } from '../../data/mocks/incidentTypes'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { SevPill } from '../../shared/ui/SevPill'

interface CatalogListProps {
  types: IncidentTypeView[]
  /** Rellena el formulario de reporte con el tipo elegido. */
  onReport: (typeKey: string) => void
}

const DETECTION_LABEL: Record<IncidentTypeView['detection'], string> = {
  AUTO: 'AUTO',
  MANUAL: 'MANUAL',
}

/** Catálogo de tipos de incidencia, filtrable por categoría. */
export function CatalogList({ types, onReport }: CatalogListProps) {
  const categoryId = useId()
  const categories = [...new Set(types.map((t) => t.category))]
  const [category, setCategory] = useState('')

  const visible = category === '' ? types : types.filter((t) => t.category === category)

  return (
    <section aria-label="Catálogo de incidencias">
      <label htmlFor={categoryId}>Categoría</label>
      <select id={categoryId} value={category} onChange={(e) => setCategory(e.target.value)}>
        <option value="">Todas las categorías</option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <p>{visible.length} tipos</p>

      <ul>
        {visible.map((type) => (
          <li key={type.key}>
            <strong>{type.name}</strong> <span>{DETECTION_LABEL[type.detection]}</span>{' '}
            <SevPill level={type.defaultSeverity} /> <EvidenceBadge state={type.evidenceState} />
            <p>Zonas típicas: {type.typicalZones.join(', ')}</p>
            <button type="button" onClick={() => onReport(type.key)}>
              Reportar
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
