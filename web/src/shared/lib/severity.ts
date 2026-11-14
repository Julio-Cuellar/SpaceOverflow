export const SEVERITIES = ['NORMAL', 'ATENCION', 'ALERTA', 'CRITICO'] as const

export type Severity = (typeof SEVERITIES)[number]

interface SeverityMeta {
  /** Forma y texto van siempre con el color: el color nunca va solo. */
  symbol: string
  label: string
  rank: number
  token: string
}

const META: Record<Severity, SeverityMeta> = {
  NORMAL: { symbol: '●', label: 'Normal', rank: 0, token: '--sev-normal' },
  ATENCION: { symbol: '▲', label: 'Atención', rank: 1, token: '--sev-atencion' },
  ALERTA: { symbol: '◆', label: 'Alerta', rank: 2, token: '--sev-alerta' },
  CRITICO: { symbol: '■', label: 'Crítico', rank: 3, token: '--sev-critico' },
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
