/** Plays a WAV and finishes when it ends. Only one answer sounds at a time. */
let current: HTMLAudioElement | null = null

export function playBlob(audio: Blob): Promise<void> {
  current?.pause()
  const url = URL.createObjectURL(audio)
  const element = new Audio(url)
  current = element
  return new Promise<void>((resolve, reject) => {
    const done = () => {
      URL.revokeObjectURL(url)
      if (current === element) current = null
    }
    element.onended = () => {
      done()
      resolve()
    }
    element.onerror = () => {
      done()
      reject(new Error('The audio could not be played.'))
    }
    element.play().catch((error: unknown) => {
      done()
      reject(error instanceof Error ? error : new Error('The audio could not be played.'))
    })
  })
}

/**
 * Client of the output voice: sends the answer to the backend (which reads it with Kokoro) and plays
 * the audio. If the service does not answer it throws an error; the answer text stays on screen.
 */
export function speakBackend(
  url: string,
  fetchImpl: typeof fetch = fetch,
  play: (audio: Blob) => Promise<void> = playBlob,
) {
  return async (text: string): Promise<void> => {
    const response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(120_000),
    })
    if (!response.ok) throw new Error(`The voice answered ${response.status}`)
    const audio = await response.blob()
    if (audio.size === 0) throw new Error('The voice returned no audio.')
    await play(audio)
  }
}
