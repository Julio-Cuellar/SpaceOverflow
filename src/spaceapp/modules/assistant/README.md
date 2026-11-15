# assistant · asistente de texto

Responde preguntas de la tripulación **solo con pasajes recuperados** y los cita. **Nunca decide ni cambia una alerta**: solo puede nombrar las activas.

## Política de respuesta (`application/ask.py`)

1. Busca pasajes con `KnowledgeQuery`. Sin pasaje relevante responde «No tengo esa información en las fuentes cargadas.» y **no llama al modelo**.
2. Con pasajes, redacta con un `LlmGateway` dentro de un **tiempo límite de 8 s**. Si el modelo tarda más, falla o no existe, responde con los pasajes en texto plano.
3. Las **citas las pone el caso de uso**, no el modelo.
4. Publica `assistant.answer_ready` (`AnswerReady`: `utterance_id`, `text`, `citations[]`). Una pregunta vacía no se guarda ni se publica.

## Adaptadores de `LlmGateway`

- `NullLlmGateway`: sin modelo; el caso de uso usa la plantilla. Es el que garantiza que todo funcione sin Ollama ni red.
- `OllamaGateway`: Ollama local en streaming (NDJSON). El modelo se indica al crearlo; no hay uno elegido todavía.

## Voz con confirmación (`application/voice.py`, F14)

1. `SubmitAudio.submit` guarda el audio (solo `webm` o `wav`) y devuelve el `utterance_id` **sin transcribir** (la ruta responderá `202`). `transcribe` corre aparte.
2. Lo transcrito queda como texto **editable**. **Nada se pregunta al asistente sin confirmar:** `ConfirmUtterance.confirm(id, texto)` pregunta con el texto que la tripulación dejó (editado o escrito) y no se puede confirmar dos veces.
3. Sin modelo de voz, con un fallo o sin habla, la intervención queda `NO_TRANSCRIPT` con el motivo y la tripulación escribe la pregunta: el flujo es el mismo.
4. Una emergencia no depende de la voz: este código no toca las alertas.

Adaptadores de `SpeechToText`: `NullSpeechToText` (sin modelo) y `WhisperSpeechToText` (`faster-whisper` en CPU, `int8`, inglés, con un texto de contexto con términos médicos) y `HttpSpeechToText` (llama al contenedor `docker/voice`, que ejecuta el anterior). Se cargan al primer uso; `build_speech_to_text` devuelve el nulo si la biblioteca no está instalada.

## Micrófono en el navegador

El navegador solo ofrece el micrófono en `localhost` o con HTTPS. En otra dirección sin HTTPS la interfaz avisa y la tripulación escribe la pregunta. La interfaz de voz está en `web/src/features/assistant/` (`VoiceInput`, `microphone.ts`); con `VITE_VOICE_URL` transcribe con Whisper real (`transcribeBackend`); sin ella, con una **simulación** que lo avisa.

## Pruebas

```bash
.venv/bin/python -m pytest tests/assistant -q
```

## Límites actuales

- **Voz (F14):** rutas `POST /api/v1/voice/utterances` (audio crudo, 202), `GET …/{id}`, `POST …/{id}/confirm` y `…/discard` (`adapters/inbound/voice_rest.py`), servidas por el servidor de desarrollo. La web consulta el estado cada 0,5 s. **Falta** la entrega por WebSocket (no existe un evento `assistant.transcript` en el contrato de Dev A) y medir la precisión con voz real (`python -m spaceapp.devtools.voice_measure`). El audio se borra al transcribirse.
- El audio se guarda tal cual en una carpeta local y no se borra: falta una política de retención.
- Conversaciones en memoria; falta el esquema `assistant` en PostgreSQL y su migración.
- Faltan los resolvers GraphQL (`askAssistant`, `conversation`), que se registran en el esquema que compone Dev A.
- La fuente de alertas activas es un puerto de solo lectura; hoy no hay adaptador real (`ActiveAlertsQuery` de Monitoreo).
