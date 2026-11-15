import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { askBackend } from "./features/assistant/askBackend";
import { speakBackend } from "./features/assistant/speakBackend";
import { Root } from "./Root";
import "@fontsource/montserrat/latin-400.css";
import "@fontsource/montserrat/latin-600.css";
import "@fontsource/montserrat/latin-700.css";
import "@fontsource/roboto/latin-400.css";
import "@fontsource/roboto/latin-500.css";
import "@fontsource/roboto/latin-700.css";
import "./console/styles.css";

/** With the assistant route (e.g. `/dev/ask`) questions go through n8n; empty, it uses the simulation. */
const assistantUrl = import.meta.env.VITE_ASSISTANT_URL;


/** With the read-aloud route (e.g. `/api/v1/voice/speak`) each answer can be listened to (Kokoro); empty, text only. */
const speakUrl = import.meta.env.VITE_SPEAK_URL;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root
      askAssistant={assistantUrl ? askBackend(assistantUrl) : undefined}
      speak={speakUrl ? speakBackend(speakUrl) : undefined}
    />
  </StrictMode>,
);
