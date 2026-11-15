/** States in which the backend is still working: ask again. */
const PENDING = new Set(['RECEIVED', 'TRANSCRIBING'])

interface UtteranceState {
  status: string
  text: string
  reason_code?: string | null
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/**
 * Client of the real voice: uploads the recording to the backend (which sends it to Whisper), polls
 * the state until there is text and returns it so the crew can correct and confirm it. If anything
 * fails it throws an error; it never returns an invented text nor silently falls back to the simulation.
 *
 * `null` means nothing was heard: the interface asks to repeat or type.
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
    if (!upload.ok) throw new Error(`The voice answered ${upload.status}`)
    const { utterance_id: id } = (await upload.json()) as { utterance_id: string }

    for (let attempt = 0; attempt < maxPolls; attempt += 1) {
      const response = await fetchImpl(`${url}/${id}`)
      if (!response.ok) throw new Error(`The voice answered ${response.status}`)
      const state = (await response.json()) as UtteranceState
      if (!PENDING.has(state.status)) {
        if (state.status === 'TRANSCRIBED' && state.text.trim() !== '') return { text: state.text }
        // "Nothing heard" asks the crew to repeat; a failed or missing voice service is an error.
        if (state.reason_code === 'FAILED' || state.reason_code === 'NO_MODEL') {
          throw new Error(`The voice is not available (${state.reason_code}).`)
        }
        return null
      }
      await sleep(pollMs)
    }
    throw new Error('The transcription took too long.')
  }
}
