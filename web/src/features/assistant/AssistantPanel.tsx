import { useId, useState } from 'react'
import { EvidenceBadge } from '../../shared/ui/EvidenceBadge'
import type { AssistantAnswer } from './mockAnswer'

interface Message {
  id: number
  role: 'crew' | 'assistant'
  text: string
  answer?: AssistantAnswer
}

interface AssistantPanelProps {
  /** Responde una pregunta. Hoy es una simulación; en I2 será `askAssistant` por GraphQL. */
  answerFor: (question: string) => AssistantAnswer
  /** Adaptador de redacción: Ollama local o nube. */
  mode: 'local' | 'nube'
}

const EXAMPLES = ['¿Por qué me duele la cabeza?', '¿Cuánto dura el mareo espacial?']

/** Chat de texto. Cada respuesta cita sus fuentes; sin pasaje, dice que no tiene información. */
export function AssistantPanel({ answerFor, mode }: AssistantPanelProps) {
  const inputId = useId()
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Message[]>([])

  const send = (raw: string) => {
    const question = raw.trim()
    if (question === '') return
    const answer = answerFor(question)
    setMessages((current) => [
      ...current,
      { id: current.length, role: 'crew', text: question },
      { id: current.length + 1, role: 'assistant', text: answer.text, answer },
    ])
    setDraft('')
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
                    {message.answer.citations.map((c) => (
                      <li key={c.documentCode}>
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

      <form
        onSubmit={(event) => {
          event.preventDefault()
          send(draft)
        }}
      >
        <label htmlFor={inputId}>Pregunta</label>
        <textarea id={inputId} value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button type="submit" disabled={draft.trim() === ''}>
          Preguntar
        </button>
      </form>
    </section>
  )
}
