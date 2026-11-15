import type { EvidenceState } from '../../shared/lib/evidence'

export interface PassageFixture {
  documentCode: string
  requirementRef: string | null
  excerpt: string
  evidenceState: EvidenceState
  /** Terms without accents or capitals, as in the backend (data/knowledge/demo_catalog.json). */
  keywords: string[]
}

/**
 * Demo passages for the assistant without a backend. They are a copy of those in the Knowledge catalog
 * and are removed when the interface consumes `askAssistant` (milestone I2).
 */
export const passagesFixture: PassageFixture[] = [
  {
    documentCode: 'OCHMO-TB-004 CO₂',
    requirementRef: null,
    excerpt:
      'Headache between 2.8 and 4.5 mmHg of ppCO₂; fatigue, poor sleep and nausea above 4.5 mmHg.',
    evidenceState: 'TB',
    keywords: ['headache', 'head', 'pain', 'co2', 'ppco2', 'fatigue', 'sleep', 'nausea'],
  },
  {
    documentCode: 'OCHMO-TB-003 Habitable Atmosphere',
    requirementRef: null,
    excerpt:
      'Hypoxia can cause mental changes sometimes imperceptible to the astronaut, reduced vision, fatigue, nausea, headache, dizziness and hyperventilation.',
    evidenceState: 'VERIFIED',
    keywords: ['hypoxia', 'headache', 'dizziness', 'vision', 'fatigue', 'nausea'],
  },
  {
    documentCode: 'OCHMO-TB-044 Medical Operations',
    requirementRef: null,
    excerpt: 'Space motion sickness lasts about 3 days on average.',
    evidenceState: 'TB',
    keywords: ['motion', 'sickness', 'space', 'days', 'dizziness'],
  },
]
