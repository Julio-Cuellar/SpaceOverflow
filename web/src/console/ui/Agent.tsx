import { useEffect, useRef, useState } from "react";
import {
  mockAnswer,
  type AssistantAnswer,
} from "../../features/assistant/mockAnswer";
import { VoiceInput } from "../../features/assistant/VoiceInput";
import { startMicrophoneRecording } from "../../features/assistant/microphone";
import type { VoiceService } from "../data/voice";
import { EvidenceBadge, Modal } from "./Common";
import type { Mode } from "../model";
interface Message {
  role: "user" | "assistant";
  text: string;
  answer?: AssistantAnswer;
}
export interface AgentProps {
  floating: boolean;
  fullPage: boolean;
  mode: Mode;
  askAssistant?: (text: string) => Promise<AssistantAnswer>;
  voice?: VoiceService;
  speak?: (text: string) => Promise<void>;
  identity?: string;
}
export function Agent({
  floating,
  fullPage,
  mode,
  askAssistant,
  voice,
  speak,
  identity,
}: AgentProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const log = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight });
  }, [messages, pending]);
  const send = async (text: string, confirmed = false) => {
    text = text.trim();
    if (!text || busy.current) return;
    busy.current = true;
    setPending(true);
    setProblem("");
    setDraft("");
    setMessages((m) => [...m, { role: "user", text }]);
    try {
      const answer =
        confirmed && voice
          ? await voice.confirm(text)
          : askAssistant
            ? await askAssistant(text)
            : mode === "demo"
              ? mockAnswer(text, [])
              : null;
      if (!answer)
        throw Error("The assistant service has not been configured.");
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text:
            answer.outcome === "ANSWERED" && !answer.citations.length
              ? "No supporting citation was returned. Consult the loaded mission sources before acting."
              : answer.text,
          answer,
        },
      ]);
    } catch (error) {
      setProblem(
        error instanceof Error
          ? error.message
          : "The assistant could not be reached.",
      );
    } finally {
      busy.current = false;
      setPending(false);
    }
  };
  const content = (
    <>
      <div className="agent-context">
        <span>
          {identity ? `Workspace: ${identity}` : "Mission knowledge assistant"}
        </span>
        <span className="tag">
          {askAssistant
            ? "Live service configured"
            : mode === "demo"
              ? "Demo response adapter"
              : "Not configured"}
        </span>
      </div>
      <div
        className="agent-log"
        role="log"
        aria-label="Conversation"
        ref={log}
        aria-live="polite"
      >
        {!messages.length && (
          <div className="agent-message">
            <p>
              Hello. Ask about the loaded mission sources. Every supported
              answer includes its references.
            </p>
            <small>The assistant never decides or modifies alerts.</small>
          </div>
        )}
        {messages.map((m, i) => (
          <article
            key={i}
            className={`agent-message ${m.role === "user" ? "user" : ""}`}
          >
            <b>{m.role === "user" ? "You" : "Mission assistant"}</b>
            <p>{m.text}</p>
            {m.answer?.degraded && (
              <p className="muted">
                Source passages shown · generation service unavailable
              </p>
            )}
            {m.answer?.citations.map((c, n) => (
              <details className="citation" key={n}>
                <summary>
                  {c.documentCode}
                  {c.requirementRef ? " · " + c.requirementRef : ""}
                </summary>
                <blockquote>{c.excerpt}</blockquote>
                <EvidenceBadge
                  state={
                    c.evidenceState === "SIMULATED" ? "DEMO" : c.evidenceState
                  }
                />
              </details>
            ))}
            {speak && m.role === "assistant" && (
              <button
                className="button subtle"
                disabled={speaking}
                onClick={() => {
                  setSpeaking(true);
                  void speak(m.text)
                    .catch(() =>
                      setProblem(
                        "Audio playback is unavailable. The answer remains on screen.",
                      ),
                    )
                    .finally(() => setSpeaking(false));
                }}
              >
                {speaking ? "Playing…" : "Listen to answer"}
              </button>
            )}
          </article>
        ))}
        {pending && <p role="status">Consulting mission sources…</p>}
      </div>
      {problem && (
        <p className="error-notice" role="alert">
          {problem}
        </p>
      )}
      <div className="suggestions">
        {[
          "What does high CO₂ mean?",
          "What sources describe oxygen conditions?",
        ].map((q) => (
          <button key={q} disabled={pending} onClick={() => setDraft(q)}>
            {q}
          </button>
        ))}
      </div>
      {voice && (
        <div className="agent-voice">
          <VoiceInput
            startRecording={startMicrophoneRecording}
            transcribe={voice.transcribe}
            onConfirm={(text) => void send(text, true)}
            onDiscard={() =>
              void voice
                .discard()
                .catch(() =>
                  setProblem(
                    "The voice turn could not be discarded on the server.",
                  ),
                )
            }
          />
        </div>
      )}
      <form
        className="agent-input"
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
      >
        <label htmlFor="agent-question">Question</label>
        <div>
          <textarea
            id="agent-question"
            rows={2}
            required
            maxLength={2000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask the mission assistant…"
          />
          <button
            className="button primary"
            disabled={pending || !draft.trim()}
          >
            Send ↑
          </button>
        </div>
        <small>
          {askAssistant
            ? "Uses the configured assistant backend."
            : "Demo answers are labeled and remain separate from telemetry."}{" "}
          Voice text requires confirmation.
        </small>
      </form>
    </>
  );
  return (
    <>
      {floating && (
        <button
          className="assistant-fab"
          onClick={() => setOpen(true)}
          aria-label="Open mission assistant"
          aria-haspopup="dialog"
          aria-expanded={open}
        >
          ✳
        </button>
      )}
      {open && floating ? (
        <Modal
          title="Mission assistant"
          className="assistant-drawer"
          onClose={() => setOpen(false)}
        >
          {content}
        </Modal>
      ) : fullPage ? (
        <section className="surface full-agent">
          <h2>Mission assistant</h2>
          {content}
        </section>
      ) : null}
    </>
  );
}
