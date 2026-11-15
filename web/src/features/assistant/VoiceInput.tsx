import { useId, useRef, useState } from 'react'

export interface Recording {
  stop: () => Promise<Blob>
}

interface VoiceInputProps {
  startRecording: () => Promise<Recording>
  /** Returns the text, or `null` if nothing was heard. Rejects if the model fails. */
  transcribe: (audio: Blob) => Promise<{ text: string } | null>
  /** Only called when the crew confirms the text. Transcribing is not acting. */
  onConfirm: (text: string) => void
  /** Notice under the transcript, e.g. that it is simulated while there is no voice model. */
  notice?: string
}

type Phase = 'idle' | 'listening' | 'transcribing' | 'review'

const TYPE_INSTEAD = 'type your question in the text box.'

/**
 * Hold to talk → editable transcript → confirm (plan, F14.3). Without a microphone, without
 * permission or with a model failure, the message says to type: text is always available.
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
      setProblem(`No microphone or no permission: ${TYPE_INSTEAD}`)
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
        setProblem(`Nothing was heard: repeat or ${TYPE_INSTEAD}`)
        return
      }
      setText(result.text)
      setPhase('review')
    } catch {
      setPhase('idle')
      setProblem(`Could not record or transcribe: ${TYPE_INSTEAD}`)
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
          Hold to talk
        </button>
      )}

      {phase === 'listening' && <p role="status">Listening…</p>}
      {phase === 'transcribing' && <p role="status">Transcribing…</p>}
      {problem !== null && <p role="alert">{problem}</p>}

      {phase === 'review' && (
        <div>
          <label htmlFor={fieldId}>Transcript (you can correct it)</label>
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
            Confirm and ask
          </button>
          <button type="button" onClick={reset}>
            Discard
          </button>
        </div>
      )}
    </div>
  )
}
