import type { DashboardView, Vital } from '../../data/mocks/fixtures'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { SevPill } from '../../shared/ui/SevPill'

interface CabinPanelProps {
  dashboard: DashboardView
}

/** Global status light and value cards. Shows what the backend computes; recomputes nothing. */
export function CabinPanel({ dashboard }: CabinPanelProps) {
  return (
    <section aria-label="Cabin panel">
      <section role="status" aria-label="Global status">
        <SevPill level={dashboard.globalSeverity} />
      </section>
      {dashboard.vitals.length === 0 ? (
        <p aria-live="polite">Waiting for simulator readings</p>
      ) : (
        <ul className="vitals">
          {dashboard.vitals.map((vital) => (
            <VitalCard key={vital.key} vital={vital} />
          ))}
        </ul>
      )}
    </section>
  )
}

function VitalCard({ vital }: { vital: Vital }) {
  const isBodySimulated = vital.domain === 'body' && vital.origin === 'SIMULATED'

  return (
    <li className="vital-card">
      <h3>{vital.label}</h3>
      <p>
        <span className="value">
          {vital.value} {vital.unit}
        </span>{' '}
        <SevPill level={vital.severity} />
      </p>
      <EvidenceBadge state={vital.evidenceState} />
      {isBodySimulated && <EvidenceBadge state="SIMULATED" />}
    </li>
  )
}
