import { useId, useState } from 'react'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import type { AssistantAnswer } from './mockAnswer'
import { VoiceInput, type Recording } from './VoiceInput'

interface Message {
  id: number
  role: 'crew' | 'assistant'
  text: string
  answer?: AssistantAnswer
}

interface AssistantPanelProps {
  /** Responde una pregunta: la simulación local (síncrona) o el asistente real (tarda). */
  answerFor: (question: string) => AssistantAnswer | Promise<AssistantAnswer>
  /** Adaptador de redacción: Ollama local o nube. */
  mode: 'local' | 'nube'
  /** Entrada por voz. Sin ella solo hay texto, que siempre está disponible. */
  voice?: {
    startRecording: () => Promise<Recording>
    transcribe: (audio: Blob) => Promise<{ text: string } | null>
    notice?: string
  }
}

const EXAMPLES = ['¿Por qué me duele la cabeza?', '¿Cuánto dura el mareo espacial?']

/** Chat de texto. Cada respuesta cita sus fuentes; sin pasaje, dice que no tiene información. */
export function AssistantPanel({ answerFor, mode, voice }: AssistantPanelProps) {
  const inputId = useId()
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)

  const send = async (raw: string) => {
    const question = raw.trim()
    if (question === '' || pending) return
    setMessages((current) => [...current, { id: current.length, role: 'crew', text: question }])
    setDraft('')
    setFailed(false)
    setPending(true)
    try {
      const answer = await answerFor(question)
      setMessages((current) => [
        ...current,
        { id: current.length, role: 'assistant', text: answer.text, answer },
      ])
    } catch {
      setFailed(true)
    } finally {
      setPending(false)
    }
  }

  return (
    <section aria-label="Asistente">
      <p>
        <span className="chip">Modo {mode}</span>
      </p>

      <ul aria-label="Preguntas de ejemplo">
        {EXAMPLES.map((example) => (
          <li key={example}>
            <button type="button" onClick={() => send(example)}>
              {example}
            </button>
          </li>
        ))}
      </ul>

      <ol aria-label="Conversación">
        {messages.map((message) => (
          <li key={message.id}>
            {message.role === 'crew' ? (
              <p>
                <strong>Tú:</strong> {message.text}
              </p>
            ) : (
              <>
                <p className="answer-text">{message.text}</p>
                {message.answer && message.answer.citations.length > 0 && (
                  <ul aria-label="Fuentes">
                    {message.answer.citations.map((c, index) => (
                      <li key={`${c.documentCode}-${index}`}>
                        <a href={`#pasaje/${encodeURIComponent(c.documentCode)}`}>
                          {c.documentCode}
                          {c.requirementRef ? ` · ${c.requirementRef}` : ''}
                        </a>{' '}
                        <EvidenceBadge state={c.evidenceState} />
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </li>
        ))}
      </ol>

      {pending && <p role="status">Consultando al asistente…</p>}
      {failed && (
        <p role="alert">No se pudo consultar el asistente. Revisa la conexión e inténtalo de nuevo.</p>
      )}

      {voice && (
        <VoiceInput
          startRecording={voice.startRecording}
          transcribe={voice.transcribe}
          notice={voice.notice}
          onConfirm={send}
        />
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault()
          send(draft)
        }}
      >
        <label htmlFor={inputId}>Pregunta</label>
        <textarea id={inputId} value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button type="submit" disabled={draft.trim() === '' || pending}>
          Preguntar
        </button>
      </form>
    </section>
  )
}
