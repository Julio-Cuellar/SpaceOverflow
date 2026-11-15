"""Servidor HTTP de Whisper para el contenedor `spaceapp-voice`: audio crudo dentro, texto fuera.

Solo biblioteca estándar y el adaptador de Whisper del proyecto (la repo se monta en `/app`).
No es parte de la aplicación: es el servicio que corre aparte, como Ollama, y el backend lo llama
por HTTP.

    python -m spaceapp.devtools.voice_server        # puerto 9000
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from spaceapp.modules.assistant.ports import SpeechToText

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # unos minutos de voz; más es un error, no una pregunta


def _handler(stt: SpeechToText) -> type[BaseHTTPRequestHandler]:
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

        def do_POST(self) -> None:
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
            except Exception as error:  # el modelo puede fallar por muchas causas
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
            return  # sin registro de cada petición: el audio es de personas

    return Handler


def build_server(stt: SpeechToText, *, host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(stt))


def main() -> None:
    from spaceapp.modules.assistant.adapters.outbound.whisper import build_speech_to_text

    stt = build_speech_to_text(os.environ.get("SPACEAPP_WHISPER_MODEL", "small"))
    host = os.environ.get("SPACEAPP_VOICE_HOST", "0.0.0.0")
    port = int(os.environ.get("SPACEAPP_VOICE_PORT", "9000"))
    print(f"Whisper ({type(stt).__name__}) en http://{host}:{port}", flush=True)
    build_server(stt, host=host, port=port).serve_forever()


if __name__ == "__main__":
    main()
