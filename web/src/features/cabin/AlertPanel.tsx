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
  causeHint: 'ENVIRONMENT' | 'BODY' | 'UNDETERMINED'
  /** Actions in catalog order: what to do first. */
  actions: AlertAction[]
  source: {
    documentCode: string
    requirementRef: string | null
    evidenceState: EvidenceState
  }
  escalateWhen: string
  /** Recommendation text; if it comes from the demo adapter, it includes the disclaimer. */
  body: string
}

const CAUSE_LABEL: Record<AlertView['causeHint'], string> = {
  ENVIRONMENT: 'air',
  BODY: 'body',
  UNDETERMINED: 'undetermined',
}

interface AlertPanelProps {
  alert: AlertView
  onAcknowledge: () => void
}

export function AlertPanel({ alert, onAcknowledge }: AlertPanelProps) {
  const requirement = alert.source.requirementRef ? ` · ${alert.source.requirementRef}` : ''

  return (
    <section
      aria-label="Alert"
      aria-live={alert.severity === 'CRITICAL' ? 'assertive' : 'off'}
    >
      <p>
        <SevPill level={alert.severity} />
      </p>

      <h3>What to do</h3>
      <ol>
        {alert.actions.map((action) => (
          <li key={action.key}>
            <strong>{action.title}</strong> <span>{action.description}</span>
          </li>
        ))}
      </ol>

      <h3>Why</h3>
      <p>{alert.ruleText}</p>
      <p>Measured: {alert.measured}</p>
      <p>Probable cause: {CAUSE_LABEL[alert.causeHint]}</p>
      <p>
        Source: {alert.source.documentCode}
        {requirement} <EvidenceBadge state={alert.source.evidenceState} />
      </p>
      <p>{alert.body}</p>

      <h3>When to escalate</h3>
      <p>{alert.escalateWhen}</p>

      <button type="button" onClick={onAcknowledge}>
        Acknowledge
      </button>
    </section>
  )
}
