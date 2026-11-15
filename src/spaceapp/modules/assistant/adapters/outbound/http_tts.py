"""Text to speech with the voice container (`docker/voice`): text goes over HTTP, a WAV comes back.

The voice and the language live in the service (`kokoro.py`); here only the text is sent. If the
container does not answer the error is raised: the caller says the voice is not available and
keeps the text.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

DEFAULT_URL = "http://127.0.0.1:9000"


class HttpTextToSpeech:
    available = True

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        *,
        timeout_s: float = 120.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/speak"
        self._timeout_s = timeout_s
        self._opener = opener

    def speak(self, text: str) -> bytes | None:
        request = urllib.request.Request(
            self._url,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self._opener(request, timeout=self._timeout_s) as response:
            audio: bytes = response.read()
        if not audio:
            raise ValueError("the voice service returned no audio")
        return audio
