import { useState } from 'react'
import type { EvidenceState } from '../../shared/lib/evidence'
import { type Severity, severityMeta } from '../../shared/lib/severity'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'

/** Peligros del programa de investigación humana de NASA (plan, sección 2). */
export type HazardKey = 'radiacion' | 'aislamiento' | 'distancia' | 'gravedad' | 'entorno'

const HAZARD_LABEL: Record<HazardKey, string> = {
  radiacion: 'Radiación espacial',
  aislamiento: 'Aislamiento y confinamiento',
  distancia: 'Distancia de la Tierra',
  gravedad: 'Campos gravitacionales',
  entorno: 'Entorno cerrado hostil',
}

export interface BodyIndicator {
  key: string
  label: string
  value: string
  severity: Severity
  hazard: HazardKey
  evidenceState: EvidenceState
}

interface BodyMapProps {
  indicators: BodyIndicator[]
}

/** Indicadores del cuerpo. Los valores son de demostración y van marcados como simulados. */
export function BodyMap({ indicators }: BodyMapProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const selected = indicators.find((i) => i.key === selectedKey)

  return (
    <section aria-label="Cuerpo humano">
      <p>Valores simulados, de demostración</p>
      <ul>
        {indicators.map((indicator) => {
          const meta = severityMeta(indicator.severity)
          return (
            <li key={indicator.key}>
              <button
                type="button"
                aria-label={`${indicator.label}, ${meta.label}`}
                aria-pressed={selectedKey === indicator.key}
                onClick={() => setSelectedKey(indicator.key)}
              >
                <span aria-hidden="true">{meta.symbol}</span> {indicator.label}
              </button>
            </li>
          )
        })}
      </ul>
      {selected && (
        <div role="region" aria-label="Detalle">
          <h3>{selected.label}</h3>
          <p>{selected.value}</p>
          <p>Peligro del programa de NASA: {HAZARD_LABEL[selected.hazard]}</p>
          <EvidenceBadge state={selected.evidenceState} />
        </div>
      )}
    </section>
  )
}
