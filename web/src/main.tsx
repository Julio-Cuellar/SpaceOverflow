import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { askBackend } from './features/assistant/askBackend'
import { transcribeBackend } from './features/assistant/transcribeBackend'
import { Root } from './Root'
import './shared/tokens.css'
import './shared/layout.css'

/** Con la ruta del asistente (p. ej. `/dev/ask`) las preguntas pasan por n8n; vacía, usa la simulación. */
const assistantUrl = import.meta.env.VITE_ASSISTANT_URL
/** Con la ruta de voz (p. ej. `/api/v1/voice/utterances`) la grabación pasa por Whisper; vacía, simulada. */
const voiceUrl = import.meta.env.VITE_VOICE_URL

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root
      askAssistant={assistantUrl ? askBackend(assistantUrl) : undefined}
      transcribeVoice={voiceUrl ? transcribeBackend(voiceUrl, crypto.randomUUID()) : undefined}
    />
  </StrictMode>,
)
