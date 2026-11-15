import type { Recording } from './VoiceInput'

/** El navegador solo da el micrófono en `localhost` o con HTTPS (plan, F14: documentarlo en el README). */
export function microphoneAvailable(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function' &&
    typeof MediaRecorder !== 'undefined'
  )
}

/** Empieza a grabar con `MediaRecorder`. Rechaza si no hay micrófono o la tripulación niega el permiso. */
export async function startMicrophoneRecording(): Promise<Recording> {
  if (!microphoneAvailable()) {
    throw new Error('Este navegador no ofrece micrófono (hace falta localhost o HTTPS).')
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
          // Suelta el micrófono: el indicador del navegador debe apagarse al soltar el botón.
          stream.getTracks().forEach((track) => track.stop())
          resolve(new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }))
        }
        recorder.stop()
      }),
  }
}
