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

/** Six metrics of a zone. Pausing freezes the readings; resuming catches them up. */
export function ZoneCharts({ zoneName, series }: ZoneChartsProps) {
  const keys = Object.keys(series)
  const [selectedKey, setSelectedKey] = useState(keys[0])
  const [frozen, setFrozen] = useState<Record<string, ZoneSeries> | null>(null)

  const paused = frozen !== null
  const view = frozen ?? series
  const current = view[selectedKey]

  return (
    <section aria-label={`${zoneName} atmosphere`}>
      <div role="tablist" aria-label="Metrics">
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

      <p>{paused ? 'Paused' : 'Live'}</p>
      <button type="button" onClick={() => setFrozen(paused ? null : series)}>
        {paused ? 'Resume' : 'Pause'}
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
