"""Adaptadores de voz de salida: el nulo y el que habla con el contenedor. Sin red."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from spaceapp.modules.assistant.adapters.outbound.http_tts import HttpTextToSpeech
from spaceapp.modules.assistant.adapters.outbound.null_tts import NullTextToSpeech

WAV = b"RIFF....WAVEfmt fake-wav-bytes"


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def opener(sent: list[dict[str, Any]], reply: bytes = WAV, fail: Exception | None = None) -> Any:
    def open_url(request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        sent.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data),  # type: ignore[arg-type]
                "content_type": request.get_header("Content-type"),
                "timeout": timeout,
            }
        )
        if fail is not None:
            raise fail
        return FakeResponse(reply)

    return open_url


def test_the_null_adapter_says_it_is_not_available_and_speaks_nothing() -> None:
    tts = NullTextToSpeech()

    assert tts.available is False
    assert tts.speak("hello") is None


def test_it_posts_the_text_as_json_to_the_speak_endpoint_and_returns_the_wav() -> None:
    sent: list[dict[str, Any]] = []
    tts = HttpTextToSpeech("http://voice:9000/", opener=opener(sent))

    audio = tts.speak("The minimum cabin pressure is 5.0 psia.")

    assert audio == WAV
    assert sent[0]["url"] == "http://voice:9000/speak"
    assert sent[0]["body"] == {"text": "The minimum cabin pressure is 5.0 psia."}
    assert sent[0]["content_type"] == "application/json"


def test_it_is_available_because_it_only_needs_the_container_to_answer() -> None:
    assert HttpTextToSpeech("http://v", opener=opener([])).available is True


def test_the_request_has_a_time_limit() -> None:
    sent: list[dict[str, Any]] = []

    HttpTextToSpeech("http://v", timeout_s=9.5, opener=opener(sent)).speak("hi")

    assert sent[0]["timeout"] == 9.5


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError("refused"), TimeoutError("too slow"), ConnectionResetError()],
)
def test_a_network_failure_is_raised_so_the_route_can_say_voice_is_unavailable(
    failure: Exception,
) -> None:
    tts = HttpTextToSpeech("http://v", opener=opener([], fail=failure))

    with pytest.raises(OSError):
        tts.speak("hi")


def test_an_empty_reply_is_an_error_not_silence() -> None:
    tts = HttpTextToSpeech("http://v", opener=opener([], reply=b""))

    with pytest.raises(ValueError):
        tts.speak("hi")
