export const EVIDENCE_STATES = ['VERIFIED', 'TB', 'DEMO', 'SIMULATED', 'UNVERIFIED'] as const

export type EvidenceState = (typeof EVIDENCE_STATES)[number]

export const EVIDENCE_META: Record<EvidenceState, { label: string; title: string }> = {
  VERIFIED: {
    label: 'VERIFIED',
    title: 'Value verified in a NASA document',
  },
  TB: {
    label: 'TB',
    title: 'NASA Technical Brief (OCHMO): reference, not a standard',
  },
  DEMO: {
    label: 'DEMO',
    title: 'Demo data: not from NASA and not verified',
  },
  SIMULATED: {
    label: 'SIMULATED',
    title: 'Simulated data for the demonstration',
  },
  UNVERIFIED: {
    label: 'UNVERIFIED',
    title: 'No verified source',
  },
}
