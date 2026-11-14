import { useState } from 'react'
import type { EvidenceState } from '../../shared/lib/evidence'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { LineChart } from '../charts/LineChart'
import type { Point } from '../charts/series'

export interface ZoneSeries {
  label: string
  unit: string
  points: Point[]
  evidenceState: EvidenceState
  threshold?: { value: number; label: string }
  anomaly?: boolean
}

interface ZoneChartsProps {
  zoneName: string
  series: Record<string, ZoneSeries>
}

/** Seis métricas de una zona. Al pausar se congelan las lecturas; al reanudar se ponen al día. */
export function ZoneCharts({ zoneName, series }: ZoneChartsProps) {
  const keys = Object.keys(series)
  const [selectedKey, setSelectedKey] = useState(keys[0])
  const [frozen, setFrozen] = useState<Record<string, ZoneSeries> | null>(null)

  const paused = frozen !== null
  const view = frozen ?? series
  const current = view[selectedKey]

  return (
    <section aria-label={`Atmósfera de ${zoneName}`}>
      <div role="tablist" aria-label="Métricas">
        {keys.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={key === selectedKey}
            onClick={() => setSelectedKey(key)}
          >
            {view[key].label}
          </button>
        ))}
      </div>

      <p>{paused ? 'En pausa' : 'En vivo'}</p>
      <button type="button" onClick={() => setFrozen(paused ? null : series)}>
        {paused ? 'Reanudar' : 'Pausar'}
      </button>

      <LineChart
        label={current.label}
        unit={current.unit}
        points={current.points}
        threshold={current.threshold}
        anomaly={current.anomaly}
      />
      <EvidenceBadge state={current.evidenceState} />
    </section>
  )
}
