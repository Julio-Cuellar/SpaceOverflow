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
  /** Answers a question. Today it is a simulation; in I2 it will be `askAssistant` over GraphQL. */
  answerFor: (question: string) => AssistantAnswer
  /** Wording adapter: local Ollama or cloud. */
  mode: 'local' | 'cloud'
}

const EXAMPLES = ['Why do I have a headache?', 'How long does space sickness last?']

/** Text chat. Each answer cites its sources; with no passage, it says it has no information. */
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
    <section aria-label="Assistant">
      <p>
        <span className="chip">{mode === 'local' ? 'Local mode' : 'Cloud mode'}</span>
      </p>

      <ul aria-label="Example questions">
        {EXAMPLES.map((example) => (
          <li key={example}>
            <button type="button" onClick={() => send(example)}>
              {example}
            </button>
          </li>
        ))}
      </ul>

      <ol aria-label="Conversation">
        {messages.map((message) => (
          <li key={message.id}>
            {message.role === 'crew' ? (
              <p>
                <strong>You:</strong> {message.text}
              </p>
            ) : (
              <>
                <p className="answer-text">{message.text}</p>
                {message.answer && message.answer.citations.length > 0 && (
                  <ul aria-label="Sources">
                    {message.answer.citations.map((c) => (
                      <li key={c.documentCode}>
                        <a href={`#passage/${encodeURIComponent(c.documentCode)}`}>
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
        <label htmlFor={inputId}>Question</label>
        <textarea id={inputId} value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button type="submit" disabled={draft.trim() === ''}>
          Ask
        </button>
      </form>
    </section>
  )
}
