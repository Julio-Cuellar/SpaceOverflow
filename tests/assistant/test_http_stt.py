"""Adaptador de voz que habla con el contenedor de Whisper. Sin red: el `opener` es de mentira."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from spaceapp.modules.assistant.adapters.outbound.http_stt import HttpSpeechToText


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def opener(sent: list[dict[str, Any]], reply: Any = None, fail: Exception | None = None) -> Any:
    def open_url(request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        sent.append(
            {
                "url": request.full_url,
                "body": request.data,
                "content_type": request.get_header("Content-type"),
                "timeout": timeout,
            }
        )
        if fail is not None:
            raise fail
        default = {"text": "what is the cabin pressure", "confidence": 0.9, "language": "en"}
        return FakeResponse(json.dumps(reply if reply is not None else default).encode())

    return open_url


def test_it_is_available_because_it_only_needs_the_container_to_answer() -> None:
    assert HttpSpeechToText("http://voice:9000", opener=opener([])).available is True


def test_it_posts_the_raw_audio_with_its_content_type_to_the_transcribe_endpoint() -> None:
    sent: list[dict[str, Any]] = []
    stt = HttpSpeechToText("http://voice:9000/", opener=opener(sent))

    stt.transcribe(b"RIFFaudio", "audio/webm")

    assert sent[0]["url"] == "http://voice:9000/transcribe"
    assert sent[0]["body"] == b"RIFFaudio"
    assert sent[0]["content_type"] == "audio/webm"


def test_it_returns_the_transcript_the_container_made() -> None:
    transcript = HttpSpeechToText("http://voice:9000", opener=opener([])).transcribe(
        b"a", "audio/wav"
    )

    assert transcript is not None
    assert transcript.text == "what is the cabin pressure"
    assert transcript.confidence == 0.9
    assert transcript.language == "en"


def test_a_missing_confidence_stays_missing() -> None:
    reply = {"text": "hello", "confidence": None, "language": "en"}

    transcript = HttpSpeechToText("http://v", opener=opener([], reply=reply)).transcribe(
        b"a", "audio/wav"
    )

    assert transcript is not None
    assert transcript.confidence is None


def test_the_request_has_a_time_limit() -> None:
    sent: list[dict[str, Any]] = []

    HttpSpeechToText("http://v", timeout_s=7.5, opener=opener(sent)).transcribe(b"a", "audio/wav")

    assert sent[0]["timeout"] == 7.5


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError("connection refused"), TimeoutError("too slow"), ConnectionResetError()],
)
def test_a_network_failure_is_raised_so_the_use_case_leaves_the_text_box_open(
    failure: Exception,
) -> None:
    stt = HttpSpeechToText("http://v", opener=opener([], fail=failure))

    with pytest.raises(OSError):
        stt.transcribe(b"a", "audio/wav")


@pytest.mark.parametrize("reply", [{"error": "boom"}, ["not", "an", "object"], {"text": 5}])
def test_a_reply_without_text_is_an_error(reply: Any) -> None:
    stt = HttpSpeechToText("http://v", opener=opener([], reply=reply))

    with pytest.raises(ValueError):
        stt.transcribe(b"a", "audio/wav")
