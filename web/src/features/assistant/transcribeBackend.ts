/** Estados en los que el backend sigue trabajando: hay que volver a preguntar. */
const PENDING = new Set(['RECEIVED', 'TRANSCRIBING'])

interface UtteranceState {
  status: string
  text: string
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/**
 * Cliente de la voz real: sube la grabación al backend (que la manda a Whisper), pregunta el estado
 * hasta que haya texto y lo devuelve para que la tripulación lo corrija y lo confirme. Si algo falla
 * lanza un error; nunca devuelve un texto inventado ni cae en silencio a la simulación.
 *
 * `null` significa que no se oyó nada o que no hay modelo de voz: la interfaz manda a escribir.
 */
export function transcribeBackend(
  url: string,
  conversationId: string,
  fetchImpl: typeof fetch = fetch,
  pollMs = 500,
  maxPolls = 120,
) {
  return async (audio: Blob): Promise<{ text: string } | null> => {
    const upload = await fetchImpl(`${url}?conversation_id=${encodeURIComponent(conversationId)}`, {
      method: 'POST',
      headers: { 'content-type': audio.type || 'audio/webm' },
      body: audio,
    })
    if (!upload.ok) throw new Error(`La voz respondió ${upload.status}`)
    const { utterance_id: id } = (await upload.json()) as { utterance_id: string }

    for (let attempt = 0; attempt < maxPolls; attempt += 1) {
      const response = await fetchImpl(`${url}/${id}`)
      if (!response.ok) throw new Error(`La voz respondió ${response.status}`)
      const state = (await response.json()) as UtteranceState
      if (!PENDING.has(state.status)) {
        return state.status === 'TRANSCRIBED' && state.text.trim() !== '' ? { text: state.text } : null
      }
      await sleep(pollMs)
    }
    throw new Error('La transcripción tardó demasiado.')
  }
}
