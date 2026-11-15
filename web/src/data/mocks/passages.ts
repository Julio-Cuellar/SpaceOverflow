import type { EvidenceState } from '../../shared/lib/evidence'

export interface PassageFixture {
  documentCode: string
  requirementRef: string | null
  excerpt: string
  evidenceState: EvidenceState
  /** Términos sin acentos ni mayúsculas, igual que en el backend (data/knowledge/demo_catalog.json). */
  keywords: string[]
}

/**
 * Pasajes de demostración para el asistente sin backend. Son copia de los del catálogo de Conocimiento
 * y se retiran cuando la interfaz consuma `askAssistant` (hito I2).
 */
export const passagesFixture: PassageFixture[] = [
  {
    documentCode: 'OCHMO-TB-004 CO₂',
    requirementRef: null,
    excerpt:
      'Dolor de cabeza entre 2.8 y 4.5 mmHg de ppCO₂; fatiga, mal sueño y náuseas por encima de 4.5 mmHg.',
    evidenceState: 'TB',
    keywords: ['cabeza', 'dolor', 'co2', 'ppco2', 'fatiga', 'sueno', 'nauseas'],
  },
  {
    documentCode: 'OCHMO-TB-003 atmósfera habitable',
    requirementRef: null,
    excerpt:
      'La hipoxia puede causar cambios mentales a veces imperceptibles para el propio astronauta, visión reducida, fatiga, náuseas, dolor de cabeza, mareo e hiperventilación.',
    evidenceState: 'VERIFICADO',
    keywords: ['hipoxia', 'cabeza', 'mareo', 'vision', 'fatiga', 'nauseas'],
  },
  {
    documentCode: 'OCHMO-TB-044 operaciones médicas',
    requirementRef: null,
    excerpt: 'El mareo espacial dura unos 3 días en promedio.',
    evidenceState: 'TB',
    keywords: ['mareo', 'espacial', 'dias'],
  },
]
