export const SEVERITIES = ['NORMAL', 'ATTENTION', 'ALERT', 'CRITICAL'] as const

export type Severity = (typeof SEVERITIES)[number]

interface SeverityMeta {
  /** Shape and text always accompany the color: color is never alone. */
  symbol: string
  label: string
  rank: number
  token: string
}

const META: Record<Severity, SeverityMeta> = {
  NORMAL: { symbol: '●', label: 'Normal', rank: 0, token: '--sev-normal' },
  ATTENTION: { symbol: '▲', label: 'Attention', rank: 1, token: '--sev-attention' },
  ALERT: { symbol: '◆', label: 'Alert', rank: 2, token: '--sev-alert' },
  CRITICAL: { symbol: '■', label: 'Critical', rank: 3, token: '--sev-critical' },
}

export function severityMeta(level: Severity): SeverityMeta {
  return META[level]
}

export function worstSeverity(levels: readonly Severity[]): Severity {
  return levels.reduce<Severity>(
    (worst, level) => (META[level].rank > META[worst].rank ? level : worst),
    'NORMAL',
  )
}
