import type { EvidenceState } from '../../shared/lib/evidence'
import type { Severity } from '../../shared/lib/severity'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import { SevPill } from '../../shared/ui/SevPill'

export interface AlertAction {
  key: string
  title: string
  description: string
}

export interface AlertView {
  severity: Severity
  ruleText: string
  measured: string
  causeHint: 'AMBIENTE' | 'CUERPO' | 'INDETERMINADO'
  /** Acciones en el orden del catálogo: primero qué hacer. */
  actions: AlertAction[]
  source: {
    documentCode: string
    requirementRef: string | null
    evidenceState: EvidenceState
  }
  escalateWhen: string
  /** Texto de la recomendación; si viene del adaptador demo, incluye la aclaración. */
  body: string
}

const CAUSE_LABEL: Record<AlertView['causeHint'], string> = {
  AMBIENTE: 'aire',
  CUERPO: 'cuerpo',
  INDETERMINADO: 'indeterminada',
}

interface AlertPanelProps {
  alert: AlertView
  onAcknowledge: () => void
}

export function AlertPanel({ alert, onAcknowledge }: AlertPanelProps) {
  const requirement = alert.source.requirementRef ? ` · ${alert.source.requirementRef}` : ''

  return (
    <section
      aria-label="Alerta"
      aria-live={alert.severity === 'CRITICO' ? 'assertive' : 'off'}
    >
      <p>
        <SevPill level={alert.severity} />
      </p>

      <h3>Qué hacer</h3>
      <ol>
        {alert.actions.map((action) => (
          <li key={action.key}>
            <strong>{action.title}</strong> <span>{action.description}</span>
          </li>
        ))}
      </ol>

      <h3>Por qué</h3>
      <p>{alert.ruleText}</p>
      <p>Medido: {alert.measured}</p>
      <p>Causa probable: {CAUSE_LABEL[alert.causeHint]}</p>
      <p>
        Fuente: {alert.source.documentCode}
        {requirement} <EvidenceBadge state={alert.source.evidenceState} />
      </p>
      <p>{alert.body}</p>

      <h3>Cuándo escalar</h3>
      <p>{alert.escalateWhen}</p>

      <button type="button" onClick={onAcknowledge}>
        Reconocer
      </button>
    </section>
  )
}
