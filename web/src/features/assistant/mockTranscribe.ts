/**
 * Simulated transcript for the demo without a backend: no voice model is used. It is removed when the
 * interface sends the audio to `POST /api/v1/voice/utterances` and receives the real transcript.
 */
export const SIMULATED_TRANSCRIPT_NOTICE =
  'Simulated transcript: no voice model is connected yet. Correct it or type your question.'

export async function mockTranscribe(): Promise<{ text: string }> {
  return { text: 'Why do I have a headache?' }
}
