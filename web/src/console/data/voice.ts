import { restJson } from "./backend";
import type {
  AssistantAnswer,
  AssistantCitation,
} from "../../features/assistant/mockAnswer";
interface WireAnswer {
  outcome: "ANSWERED" | "NO_INFO";
  text: string;
  citations: {
    document_code: string;
    requirement_ref: string | null;
    excerpt: string;
    evidence_state: AssistantCitation["evidenceState"];
  }[];
  degraded?: boolean;
  composed_by?: string;
}
export function voiceService(url: string) {
  let utteranceId: string | null = null;
  let controller: AbortController | null = null;
  return {
    transcribe: async (audio: Blob) => {
      controller?.abort();
      controller = new AbortController();
      const signal = controller.signal;
      const result = await restJson<{ utterance_id: string }>(
        `${url}?conversation_id=${crypto.randomUUID()}`,
        {
          method: "POST",
          headers: { "content-type": audio.type || "audio/webm" },
          body: audio,
          signal,
        },
      );
      utteranceId = result.utterance_id;
      for (let n = 0; n < 120; n++) {
        const state = await restJson<{
          status: string;
          text: string;
          reason_code?: string;
        }>(`${url}/${encodeURIComponent(utteranceId)}`, { signal });
        if (state.status === "TRANSCRIBED" && state.text.trim())
          return { text: state.text };
        if (!["RECEIVED", "TRANSCRIBING"].includes(state.status)) {
          if (state.reason_code === "NO_SPEECH") return null;
          throw Error(
            "Voice transcription is unavailable. Type your question instead.",
          );
        }
        await new Promise<void>((resolve, reject) => {
          const onAbort = () => {
            clearTimeout(timer);
            reject(new DOMException("Aborted", "AbortError"));
          };
          const timer = setTimeout(() => {
            signal.removeEventListener("abort", onAbort);
            resolve();
          }, 500);
          signal.addEventListener("abort", onAbort, { once: true });
        });
      }
      throw Error("Voice transcription timed out. Type your question instead.");
    },
    confirm: async (text: string): Promise<AssistantAnswer> => {
      if (!utteranceId) throw Error("No transcript is awaiting confirmation.");
      const answer = await restJson<WireAnswer>(
        `${url}/${encodeURIComponent(utteranceId)}/confirm`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ text }),
          signal: AbortSignal.timeout(150000),
        },
        fetch,
        150000,
      );
      utteranceId = null;
      return {
        outcome: answer.outcome,
        degraded: answer.degraded,
        composedBy: answer.composed_by,
        text: answer.text,
        citations: answer.citations.map((c) => ({
          documentCode: c.document_code,
          requirementRef: c.requirement_ref,
          excerpt: c.excerpt,
          evidenceState: c.evidence_state,
        })),
      };
    },
    discard: async () => {
      controller?.abort();
      if (utteranceId) {
        const id = utteranceId;
        utteranceId = null;
        await restJson(`${url}/${encodeURIComponent(id)}/discard`, {
          method: "POST",
        });
      }
    },
  };
}
export type VoiceService = ReturnType<typeof voiceService>;
