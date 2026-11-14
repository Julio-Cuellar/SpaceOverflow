import { passagesFixture, type PassageFixture } from '../../data/mocks/passages'
import type { EvidenceState } from '../../shared/lib/evidence'

export const NO_INFO_TEXT = 'No tengo esa información en las fuentes cargadas.'
const ALERT_NOTE = 'Esta respuesta no cambia la alerta.'
const TOP_K = 3
const MIN_TERM_LENGTH = 4

export interface AssistantCitation {
  documentCode: string
  requirementRef: string | null
  excerpt: string
  evidenceState: EvidenceState
}

export interface AssistantAnswer {
  outcome: 'ANSWERED' | 'NO_INFO'
  text: string
  citations: AssistantCitation[]
}

/** Minúsculas y sin acentos. «CO₂» queda como «co2» (igual que la búsqueda del backend). */
function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
}

function terms(text: string): Set<string> {
  const words = normalize(text).match(/[a-z0-9]+/g) ?? []
  return new Set(words.filter((w) => w.length >= MIN_TERM_LENGTH))
}

function sourceLabel(p: PassageFixture): string {
  const requirement = p.requirementRef ? ` · ${p.requirementRef}` : ''
  return `${p.documentCode}${requirement} · ${p.evidenceState}`
}

/**
 * Misma política que el caso de uso del backend: solo pasajes recuperados, con cita; sin pasaje,
 * «No tengo esa información»; una alerta activa se nombra pero nunca se cambia.
 */
export function mockAnswer(question: string, activeAlerts: string[]): AssistantAnswer {
  const query = terms(question)
  const found = passagesFixture
    .map((passage) => ({
      passage,
      score: passage.keywords.filter((k) => query.has(k)).length,
    }))
    .filter((entry) => entry.score >= 1)
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_K)
    .map((entry) => entry.passage)

  if (found.length === 0) {
    return { outcome: 'NO_INFO', text: NO_INFO_TEXT, citations: [] }
  }

  const lines = [
    'Según las fuentes cargadas:',
    ...found.map((p) => `- ${p.excerpt} (${sourceLabel(p)})`),
    ...activeAlerts.map((title) => `Alerta activa: ${title}. ${ALERT_NOTE}`),
  ]
  return {
    outcome: 'ANSWERED',
    text: lines.join('\n'),
    citations: found.map(({ documentCode, requirementRef, excerpt, evidenceState }) => ({
      documentCode,
      requirementRef,
      excerpt,
      evidenceState,
    })),
  }
}
