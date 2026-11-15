# assistant · crew assistant

Answers crew questions **only with retrieved passages** and cites them. It **never decides or changes an alert**: it can only name the active ones. It always answers in English.

## Answer policy (`application/ask.py`)

1. The question goes to the n8n agent (`AssistantOrchestrator`), which calls the `search_passages` tool of this backend. The tool records what it returns: **the citations come from there**, not from what the model says.
2. The agent's text is delivered only if it passes the checks: it retrieved at least one passage, it is in English (`language.py`), it does not refuse ("I don't have that information") after retrieving passages, and every figure comes from a passage, the question or an alert (`grounding.py`). Otherwise the answer is the **template**.
3. The template shows, for each passage, only the sentence that answers the question (`brief.py`, extractive: nothing is rewritten). The citations keep the full excerpt.
4. Without a relevant passage the answer is "I don't have that information in the loaded sources." and **no model is called**. If n8n fails or is slow (limit configurable), the backend goes through the same checks with the local `LlmGateway`, or answers with the passages as plain text.
5. It publishes `assistant.answer_ready` (`AnswerReady`: `utterance_id`, `text`, `citations[]`). An empty question is neither stored nor published.

## `LlmGateway` adapters

- `NullLlmGateway`: no model; the use case uses the template. It guarantees everything works without Ollama or network.
- `OllamaGateway`: local Ollama in streaming (NDJSON).
- `N8nOrchestrator`: the n8n agent (`n8n/README.md`).

## Voice with confirmation (`application/voice.py`, F14)

1. `SubmitAudio.submit` stores the audio (only `webm` or `wav`) and returns the `utterance_id` **without transcribing** (the route answers `202`). `transcribe` runs apart and **deletes the audio** as soon as there is text or it is known there is none.
2. What was transcribed stays as **editable** text. **Nothing is asked of the assistant without confirming:** `ConfirmUtterance.confirm(id, text)` asks with the text the crew left (edited or typed) and cannot be confirmed twice.
3. Without a voice model, with a failure or without speech, the utterance stays `NO_TRANSCRIPT` with the reason (`reason_code`: `NO_SPEECH`, `FAILED`, `NO_MODEL`) and the crew types the question: the flow is the same.
4. An emergency does not depend on voice: this code does not touch the alerts.

`SpeechToText` adapters: `NullSpeechToText` (no model), `WhisperSpeechToText` (`faster-whisper` on CPU, `int8`, English, with a context text of medical terms) and `HttpSpeechToText` (calls the `docker/voice` container, which runs the previous one). They load on first use; `build_speech_to_text` returns the null one if the library is not installed.

## Reading answers aloud (output voice)

`POST /api/v1/voice/speak` (`{"text": ...}` → WAV) reads the answer with Kokoro-82M through the `docker/voice` container (`TextToSpeech` port: `NullTextToSpeech`, `HttpTextToSpeech`, `KokoroTextToSpeech`). Before reading, the sources block is removed and the units are spelled out (`speakable.py`, max. 400 characters). Without a service the route answers 503 and the answer stays on screen.

## Microphone in the browser

The browser only offers the microphone on `localhost` or over HTTPS. At another address without HTTPS the interface warns and the crew types the question. The voice interface is in `web/src/features/assistant/` (`VoiceInput`, `microphone.ts`, `transcribeBackend.ts`, `speakBackend.ts`): with `VITE_VOICE_URL` it transcribes with the real Whisper, and with `VITE_SPEAK_URL` it offers "Listen to the answer" and "Read answers aloud"; without them, a **simulated** transcript that says so, and text-only answers.

## Tests

```bash
.venv/bin/python -m pytest tests/assistant -q
```

## Current limits

- **Voice routes:** `POST /api/v1/voice/utterances` (raw audio, 202), `GET .../{id}`, `POST .../{id}/confirm` and `.../discard` (`adapters/inbound/voice_rest.py`), served by the development server. The web polls the state every 0.5 s. **Missing:** delivery over WebSocket (there is no `assistant.transcript` event in Dev A's contract) and measuring accuracy with real voice beyond the first 10 phrases (`python -m spaceapp.devtools.voice_measure`).
- Whisper can repeat its context text when the audio has no clear speech; there is no guard yet.
- Conversations in memory; the `assistant` schema in PostgreSQL and its migration are missing.
- The GraphQL resolvers (`askAssistant`, `conversation`) are missing; they are registered in the schema Dev A composes.
- The active alerts source is a read-only port; today there is no real adapter (Monitoring's `ActiveAlertsQuery`).
