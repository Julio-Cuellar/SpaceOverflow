import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { askBackend } from "./features/assistant/askBackend";
import { speakBackend } from "./features/assistant/speakBackend";
import { transcribeBackend } from "./features/assistant/transcribeBackend";
import { Root } from "./Root";
import "./shared/tokens.css";
import "./shared/layout.css";

/** With the assistant route (e.g. `/dev/ask`) questions go through n8n; empty, it uses the simulation. */
const assistantUrl = import.meta.env.VITE_ASSISTANT_URL;
/** With the voice route (e.g. `/api/v1/voice/utterances`) the recording goes through Whisper; empty, simulated. */
const voiceUrl = import.meta.env.VITE_VOICE_URL;
/** With the read-aloud route (e.g. `/api/v1/voice/speak`) each answer can be listened to (Kokoro); empty, text only. */
const speakUrl = import.meta.env.VITE_SPEAK_URL;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root
      askAssistant={assistantUrl ? askBackend(assistantUrl) : undefined}
      transcribeVoice={
        voiceUrl ? transcribeBackend(voiceUrl, crypto.randomUUID()) : undefined
      }
      speak={speakUrl ? speakBackend(speakUrl) : undefined}
    />
  </StrictMode>,
);
