"""Voz a texto con el contenedor de Whisper (`docker/voice`): audio crudo por HTTP, texto de vuelta.

El idioma y el texto de contexto con términos médicos viven en `whisper.py`, que es lo que corre
dentro del contenedor: aquí solo se envía el audio. Si el contenedor no responde, se lanza el error
y el caso de uso deja la transcripción en blanco para que la tripulación escriba la pregunta.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from spaceapp.modules.assistant.domain.voice import Transcript

DEFAULT_URL = "http://127.0.0.1:9000"


class HttpSpeechToText:
    available = True

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        *,
        timeout_s: float = 120.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/transcribe"
        self._timeout_s = timeout_s
        self._opener = opener

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        request = urllib.request.Request(
            self._url, data=audio, headers={"Content-Type": content_type}, method="POST"
        )
        with self._opener(request, timeout=self._timeout_s) as response:
            payload = json.load(response)
        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str):
            raise ValueError(f"el servicio de voz no devolvió texto: {payload!r}")
        confidence = payload.get("confidence")
        language = payload.get("language")
        return Transcript(
            text=text,
            confidence=float(confidence) if confidence is not None else None,
            language=language if isinstance(language, str) else None,
        )
