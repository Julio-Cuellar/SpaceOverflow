export const EVIDENCE_STATES = ['VERIFICADO', 'TB', 'DEMO', 'SIMULADO', 'NO_VERIFICADO'] as const

export type EvidenceState = (typeof EVIDENCE_STATES)[number]

export const EVIDENCE_META: Record<EvidenceState, { label: string; title: string }> = {
  VERIFICADO: {
    label: 'VERIFICADO',
    title: 'Valor verificado en un documento de NASA',
  },
  TB: {
    label: 'TB',
    title: 'Technical Brief de NASA (OCHMO): referencia, no norma',
  },
  DEMO: {
    label: 'DEMO',
    title: 'Dato de demostración: no es de NASA ni está verificado',
  },
  SIMULADO: {
    label: 'SIMULADO',
    title: 'Dato simulado para la demostración',
  },
  NO_VERIFICADO: {
    label: 'NO VERIFICADO',
    title: 'Sin fuente verificada',
  },
}
