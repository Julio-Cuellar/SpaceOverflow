"""Voice HTTP server for the `spaceapp-voice` container: Whisper (hearing) and Kokoro (speech).

    POST /transcribe   raw audio in, text out
    POST /speak        {"text": ...} in, WAV out
    GET  /health

Only the standard library and the project's Whisper adapter (the repo is mounted at `/app`).
It is not part of the application: it is the service that runs apart, like Ollama, and the
backend calls it over HTTP.

    python -m spaceapp.devtools.voice_server        # port 9000
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from spaceapp.modules.assistant.ports import SpeechToText, TextToSpeech

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # a few minutes of speech; more is an error, not a question
MAX_TEXT_BYTES = 64 * 1024  # the text read aloud already arrives trimmed


def _handler(stt: SpeechToText, tts: TextToSpeech | None) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def _speak(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_TEXT_BYTES:
                self._send(400, {"error": "empty or oversized text"})
                return
            try:
                text = json.loads(self.rfile.read(length)).get("text")
            except (ValueError, AttributeError):
                text = None
            if not isinstance(text, str) or not text.strip():
                self._send(400, {"error": "missing text"})
                return
            if tts is None or not tts.available:
                self._send(503, {"error": "no voice model"})
                return
            try:
                audio = tts.speak(text)
            except Exception as error:  # the model can fail for many reasons
                self._send(500, {"error": f"speech failed: {error}"})
                return
            if audio is None:
                self._send(503, {"error": "no voice model"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)

        def do_POST(self) -> None:
            if self.path == "/speak":
                self._speak()
                return
            if self.path != "/transcribe":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                self._send(400, {"error": "empty audio"})
                return
            if length > MAX_AUDIO_BYTES:
                self._send(413, {"error": "audio too large"})
                self.close_connection = True
                return
            audio = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "audio/wav")
            try:
                transcript = stt.transcribe(audio, content_type)
            except Exception as error:  # the model can fail for many reasons
                self._send(500, {"error": f"transcription failed: {error}"})
                return
            if transcript is None:
                self._send(200, {"text": "", "confidence": None, "language": None})
                return
            self._send(
                200,
                {
                    "text": transcript.text,
                    "confidence": transcript.confidence,
                    "language": transcript.language,
                },
            )

        def log_message(self, format: str, *args: Any) -> None:
            return  # no per-request logging: the audio belongs to people

    return Handler


def build_server(
    stt: SpeechToText, *, host: str, port: int, tts: TextToSpeech | None = None
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(stt, tts))


def main() -> None:
    from spaceapp.modules.assistant.adapters.outbound.kokoro import build_text_to_speech
    from spaceapp.modules.assistant.adapters.outbound.whisper import build_speech_to_text

    stt = build_speech_to_text(os.environ.get("SPACEAPP_WHISPER_MODEL", "small"))
    tts = build_text_to_speech(Path(os.environ.get("SPACEAPP_KOKORO_DIR", "/kokoro")))
    host = os.environ.get("SPACEAPP_VOICE_HOST", "0.0.0.0")
    port = int(os.environ.get("SPACEAPP_VOICE_PORT", "9000"))
    print(
        f"Hearing: {type(stt).__name__} · voice: {type(tts).__name__} · http://{host}:{port}",
        flush=True,
    )
    build_server(stt, host=host, port=port, tts=tts).serve_forever()


if __name__ == "__main__":
    main()
