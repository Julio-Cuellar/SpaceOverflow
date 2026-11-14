import { EVIDENCE_META, type EvidenceState } from '../lib/evidence'

interface EvidenceBadgeProps {
  state: EvidenceState
}

export function EvidenceBadge({ state }: EvidenceBadgeProps) {
  const meta = EVIDENCE_META[state]

  return (
    <span className="evidence-badge" data-evidence={state} title={meta.title}>
      {meta.label}
    </span>
  )
}
