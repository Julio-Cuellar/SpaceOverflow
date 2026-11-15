import { passagesFixture } from '../../data/mocks/passages'
import type { EvidenceState } from '../../shared/lib/evidence'

export const NO_INFO_TEXT = "I don't have that information in the loaded sources."
const ALERT_NOTE = 'This answer does not change the alert.'
const TOP_K = 3
const MIN_TERM_LENGTH = 4

export interface AssistantCitation {
  documentCode: string
  requirementRef: string | null
  excerpt: string
  evidenceState: EvidenceState
}

export interface AssistantAnswer {
  degraded?: boolean
  composedBy?: string
  outcome: 'ANSWERED' | 'NO_INFO'
  text: string
  citations: AssistantCitation[]
}

/** Lowercase and without accents. 'CO₂' becomes 'co2' (same as the backend search). */
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

/**
 * Same policy as the backend use case: only retrieved passages, with a citation; without a passage,
 * "I don't have that information"; an active alert is named but never changed.
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
    'According to the loaded sources:',
    ...found.map((p) => `- ${p.excerpt}`),
    ...activeAlerts.map((title) => `Active alert: ${title}. ${ALERT_NOTE}`),
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
