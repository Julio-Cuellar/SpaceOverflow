import { useId, useRef, useState } from 'react'

export interface Recording {
  stop: () => Promise<Blob>
}

interface VoiceInputProps {
  startRecording: () => Promise<Recording>
  /** Devuelve el texto, o `null` si no se oyó nada. Rechaza si falla el modelo. */
  transcribe: (audio: Blob) => Promise<{ text: string } | null>
  /** Solo se llama cuando la tripulación confirma el texto. Transcribir no es actuar. */
  onConfirm: (text: string) => void
  /** Aviso bajo la transcripción, p. ej. que es simulada mientras no haya modelo de voz. */
  notice?: string
}

type Phase = 'idle' | 'listening' | 'transcribing' | 'review'

const TYPE_INSTEAD = 'escribe tu pregunta en el cuadro de texto.'

/**
 * Mantener para hablar → transcripción editable → confirmar (plan, F14.3). Sin micrófono, sin
 * permiso o con un fallo del modelo, el mensaje manda a escribir: el texto siempre está disponible.
 */
export function VoiceInput({ startRecording, transcribe, onConfirm, notice }: VoiceInputProps) {
  const fieldId = useId()
  const [phase, setPhase] = useState<Phase>('idle')
  const [text, setText] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const recording = useRef<Promise<Recording> | null>(null)
  const held = useRef(false)

  const begin = () => {
    if (held.current || phase === 'transcribing' || phase === 'review') return
    held.current = true
    setProblem(null)
    setPhase('listening')
    recording.current = startRecording()
    recording.current.catch(() => {
      held.current = false
      recording.current = null
      setPhase('idle')
      setProblem(`Sin micrófono o sin permiso: ${TYPE_INSTEAD}`)
    })
  }

  const finish = async () => {
    if (!held.current || recording.current === null) return
    held.current = false
    const pending = recording.current
    recording.current = null
    setPhase('transcribing')
    try {
      const audio = await (await pending).stop()
      const result = await transcribe(audio)
      if (result === null || result.text.trim() === '') {
        setPhase('idle')
        setProblem(`No se oyó nada: repite o ${TYPE_INSTEAD}`)
        return
      }
      setText(result.text)
      setPhase('review')
    } catch {
      setPhase('idle')
      setProblem(`No se pudo grabar o transcribir: ${TYPE_INSTEAD}`)
    }
  }

  const reset = () => {
    setPhase('idle')
    setText('')
  }

  return (
    <div>
      {phase !== 'review' && (
        <button
          type="button"
          onPointerDown={begin}
          onPointerUp={finish}
          onPointerLeave={finish}
          onKeyDown={(event) => {
            if ((event.key === ' ' || event.key === 'Enter') && !event.repeat) {
              event.preventDefault()
              begin()
            }
          }}
          onKeyUp={(event) => {
            if (event.key === ' ' || event.key === 'Enter') {
              event.preventDefault()
              void finish()
            }
          }}
        >
          Mantener para hablar
        </button>
      )}

      {phase === 'listening' && <p role="status">Escuchando…</p>}
      {phase === 'transcribing' && <p role="status">Transcribiendo…</p>}
      {problem !== null && <p role="alert">{problem}</p>}

      {phase === 'review' && (
        <div>
          <label htmlFor={fieldId}>Transcripción (puedes corregirla)</label>
          <textarea id={fieldId} value={text} onChange={(event) => setText(event.target.value)} />
          {notice && <p>{notice}</p>}
          <button
            type="button"
            disabled={text.trim() === ''}
            onClick={() => {
              onConfirm(text.trim())
              reset()
            }}
          >
            Confirmar y preguntar
          </button>
          <button type="button" onClick={reset}>
            Descartar
          </button>
        </div>
      )}
    </div>
  )
}
