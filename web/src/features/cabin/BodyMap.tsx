import { useState } from 'react'
import type { EvidenceState } from '../../shared/lib/evidence'
import { type Severity, severityMeta } from '../../shared/lib/severity'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'

/** Hazards of NASA's human research program (architecture plan, section 2). */
export type HazardKey = 'radiation' | 'isolation' | 'distance' | 'gravity' | 'environment'

const HAZARD_LABEL: Record<HazardKey, string> = {
  radiation: 'Space radiation',
  isolation: 'Isolation and confinement',
  distance: 'Distance from Earth',
  gravity: 'Gravity fields',
  environment: 'Hostile closed environment',
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

/** Body indicators. The values are demo values and are marked as simulated. */
export function BodyMap({ indicators }: BodyMapProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const selected = indicators.find((i) => i.key === selectedKey)

  return (
    <section aria-label="Human body">
      <p>Simulated values, for demonstration</p>
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
        <div role="region" aria-label="Detail">
          <h3>{selected.label}</h3>
          <p>{selected.value}</p>
          <p>NASA program hazard: {HAZARD_LABEL[selected.hazard]}</p>
          <EvidenceBadge state={selected.evidenceState} />
        </div>
      )}
    </section>
  )
}
