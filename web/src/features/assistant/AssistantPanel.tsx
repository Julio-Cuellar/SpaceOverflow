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
  /** Answers a question: the local simulation (synchronous) or the real assistant (slow). */
  answerFor: (question: string) => AssistantAnswer | Promise<AssistantAnswer>
  /** Writing adapter: local Ollama or cloud. */
  mode: 'local' | 'cloud'
  /** Voice input. Without it there is only text, which is always available. */
  voice?: {
    startRecording: () => Promise<Recording>
    transcribe: (audio: Blob) => Promise<{ text: string } | null>
    notice?: string
  }
  /** Reads an answer aloud. Without it there is no "Listen" button: the answer is text only. */
  speak?: (text: string) => Promise<void>
}

const EXAMPLES = ['Why do I have a headache?', 'How long does space motion sickness last?']

/** Text chat. Each answer cites its sources; without a passage, it says it has no information. */
export function AssistantPanel({ answerFor, mode, voice, speak }: AssistantPanelProps) {
  const inputId = useId()
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)
  const [readAloud, setReadAloud] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [speechFailed, setSpeechFailed] = useState(false)

  const read = async (text: string) => {
    if (!speak) return
    setSpeechFailed(false)
    setSpeaking(true)
    try {
      await speak(text)
    } catch {
      setSpeechFailed(true)
    } finally {
      setSpeaking(false)
    }
  }

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
      if (readAloud) void read(answer.text)
    } catch {
      setFailed(true)
    } finally {
      setPending(false)
    }
  }

  return (
    <section aria-label="Assistant">
      <p>
        <span className="chip">Mode {mode}</span>
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
                {speak && (
                  <button type="button" disabled={speaking} onClick={() => void read(message.text)}>
                    Listen to the answer
                  </button>
                )}
                {message.answer && message.answer.citations.length > 0 && (
                  <ul aria-label="Sources">
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

      {speak && (
        <p>
          <label>
            <input
              type="checkbox"
              checked={readAloud}
              onChange={(event) => setReadAloud(event.target.checked)}
            />{' '}
            Read answers aloud
          </label>
        </p>
      )}
      {speaking && <p role="status">Reading the answer…</p>}
      {speechFailed && (
        <p role="alert">Could not read it aloud: the answer stays on screen.</p>
      )}

      {pending && <p role="status">Consulting the assistant…</p>}
      {failed && (
        <p role="alert">Could not consult the assistant. Check the connection and try again.</p>
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
        <label htmlFor={inputId}>Question</label>
        <textarea id={inputId} value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button type="submit" disabled={draft.trim() === '' || pending}>
          Ask
        </button>
      </form>
    </section>
  )
}
