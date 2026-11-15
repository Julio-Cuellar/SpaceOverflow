import { type Severity, severityMeta } from '../lib/severity'

interface SevPillProps {
  level: Severity
}

export function SevPill({ level }: SevPillProps) {
  const meta = severityMeta(level)

  return (
    <span className="sev-pill" data-severity={level} style={{ color: `var(${meta.token})` }}>
      <span aria-hidden="true">{meta.symbol}</span> {meta.label}
    </span>
  )
}
