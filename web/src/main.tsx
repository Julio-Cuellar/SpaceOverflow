import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { askBackend } from './features/assistant/askBackend'
import { Root } from './Root'
import './shared/tokens.css'
import './shared/layout.css'

/** Con la ruta del asistente (p. ej. `/dev/ask`) las preguntas pasan por n8n; vacía, usa la simulación. */
const assistantUrl = import.meta.env.VITE_ASSISTANT_URL

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root askAssistant={assistantUrl ? askBackend(assistantUrl) : undefined} />
  </StrictMode>,
)
