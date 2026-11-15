import type { Recording } from './VoiceInput'

/** The browser only gives the microphone on `localhost` or over HTTPS (plan, F14: document it in the README). */
export function microphoneAvailable(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function' &&
    typeof MediaRecorder !== 'undefined'
  )
}

/** Starts recording with `MediaRecorder`. Rejects if there is no microphone or the crew denies permission. */
export async function startMicrophoneRecording(): Promise<Recording> {
  if (!microphoneAvailable()) {
    throw new Error('This browser offers no microphone (it needs localhost or HTTPS).')
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream)
  const chunks: Blob[] = []
  recorder.ondataavailable = (event) => chunks.push(event.data)
  recorder.start()

  return {
    stop: () =>
      new Promise<Blob>((resolve) => {
        recorder.onstop = () => {
          // Release the microphone: the browser indicator must turn off when the button is released.
          stream.getTracks().forEach((track) => track.stop())
          resolve(new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }))
        }
        recorder.stop()
      }),
  }
}
