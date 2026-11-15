import type { DashboardView, Vital } from '../../data/mocks/fixtures'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { SevPill } from '../../shared/ui/SevPill'

interface CabinPanelProps {
  dashboard: DashboardView
}

/** Semáforo global y tarjetas de valores. Muestra lo que calcula el backend; no recalcula nada. */
export function CabinPanel({ dashboard }: CabinPanelProps) {
  return (
    <section aria-label="Panel de cabina">
      <section role="status" aria-label="Estado global">
        <SevPill level={dashboard.globalSeverity} />
      </section>
      {dashboard.vitals.length === 0 ? (
        <p aria-live="polite">Esperando lecturas del simulador</p>
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
  const isBodySimulated = vital.domain === 'cuerpo' && vital.origin === 'SIMULATED'

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
      {isBodySimulated && <EvidenceBadge state="SIMULADO" />}
    </li>
  )
}
