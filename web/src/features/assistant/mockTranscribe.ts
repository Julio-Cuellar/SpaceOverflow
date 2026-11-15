/**
 * Transcripción simulada para la demo sin backend: no se usa ningún modelo de voz. Se retira cuando la
 * interfaz envíe el audio a `POST /api/v1/voice/utterances` y reciba la transcripción real.
 */
export const SIMULATED_TRANSCRIPT_NOTICE =
  'Transcripción simulada: aún no hay un modelo de voz conectado. Corrígela o escribe tu pregunta.'

export async function mockTranscribe(): Promise<{ text: string }> {
  return { text: '¿Por qué me duele la cabeza?' }
}
