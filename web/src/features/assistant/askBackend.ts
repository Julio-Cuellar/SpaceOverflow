import { EVIDENCE_STATES, type EvidenceState } from '../../shared/lib/evidence'
import type { AssistantAnswer, AssistantCitation } from './mockAnswer'

/** Con el modelo local una respuesta tarda entre 15 y 120 s (bitácora E19). */
const TIMEOUT_MS = 150_000

interface BackendCitation {
  document_code: string
  requirement_ref: string | null
  excerpt: string
  evidence_state: string
}

interface BackendAnswer {
  outcome: 'ANSWERED' | 'NO_INFO'
  text: string
  citations: BackendCitation[]
}

function isEvidenceState(value: string): value is EvidenceState {
  return (EVIDENCE_STATES as readonly string[]).includes(value)
}

function toCitation(citation: BackendCitation): AssistantCitation {
  if (!isEvidenceState(citation.evidence_state)) {
    throw new Error(`Estado de evidencia desconocido: ${citation.evidence_state}`)
  }
  return {
    documentCode: citation.document_code,
    requirementRef: citation.requirement_ref,
    excerpt: citation.excerpt,
    evidenceState: citation.evidence_state,
  }
}

/**
 * Cliente del asistente real: la pregunta pasa por el backend, n8n y Ollama. Si algo falla lanza
 * un error; nunca devuelve una respuesta inventada ni cae en silencio a la simulación.
 */
export function askBackend(url: string, fetchImpl: typeof fetch = fetch) {
  return async (question: string): Promise<AssistantAnswer> => {
    const response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: question }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
    if (!response.ok) throw new Error(`El asistente respondió ${response.status}`)
    const body = (await response.json()) as BackendAnswer
    return {
      outcome: body.outcome,
      text: body.text,
      citations: body.citations.map(toCitation),
    }
  }
}
