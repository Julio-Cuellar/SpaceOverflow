import { EVIDENCE_STATES, type EvidenceState } from '../../shared/lib/evidence'
import type { AssistantAnswer, AssistantCitation } from './mockAnswer'

/** With the local model an answer takes between 15 and 120 s (logbook E19). */
const TIMEOUT_MS = 150_000

interface BackendCitation {
  document_code: string
  requirement_ref: string | null
  excerpt: string
  evidence_state: string
}

interface BackendAnswer {
  degraded?: boolean
  composed_by?: string
  outcome: 'ANSWERED' | 'NO_INFO'
  text: string
  citations: BackendCitation[]
}

function isEvidenceState(value: string): value is EvidenceState {
  return (EVIDENCE_STATES as readonly string[]).includes(value)
}

function toCitation(citation: BackendCitation): AssistantCitation {
  if (!isEvidenceState(citation.evidence_state)) {
    throw new Error(`Unknown evidence state: ${citation.evidence_state}`)
  }
  return {
    documentCode: citation.document_code,
    requirementRef: citation.requirement_ref,
    excerpt: citation.excerpt,
    evidenceState: citation.evidence_state,
  }
}

/**
 * Client of the real assistant: the question goes through the backend, n8n and Ollama. If anything
 * fails it throws an error; it never returns an invented answer nor silently falls back to the simulation.
 */
export function askBackend(url: string, fetchImpl: typeof fetch = fetch) {
  return async (question: string): Promise<AssistantAnswer> => {
    const response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: question }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    if (!response.ok) throw new Error(`The assistant answered ${response.status}`)
    const body = (await response.json()) as BackendAnswer
    return {
      outcome: body.outcome,
      degraded: body.degraded,
      composedBy: body.composed_by,
      text: body.text,
      citations: body.citations.map(toCitation),
    }
  }
}
