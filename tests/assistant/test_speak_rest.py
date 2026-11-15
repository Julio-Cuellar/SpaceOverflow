"""Ruta que convierte una respuesta en voz: el texto se limpia y el audio vuelve como WAV."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from spaceapp.modules.assistant.adapters.inbound.voice_rest import build_speech_router
from spaceapp.modules.assistant.adapters.outbound.null_tts import NullTextToSpeech

WAV = b"RIFF....WAVEfake"
URL = "/api/v1/voice/speak"


class FakeTts:
    available = True

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.spoken: list[str] = []

    def speak(self, text: str) -> bytes | None:
        self.spoken.append(text)
        if self._fail:
            raise OSError("voice container down")
        return WAV


def client(tts: object) -> TestClient:
    app = FastAPI()
    app.include_router(build_speech_router(tts=tts))  # type: ignore[arg-type]
    return TestClient(app)


def test_it_returns_the_audio_as_wav() -> None:
    response = client(FakeTts()).post(URL, json={"text": "The limit is 3 mmHg."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == WAV


def test_it_reads_the_cleaned_text_not_the_sources_or_the_symbols() -> None:
    tts = FakeTts()

    client(tts).post(URL, json={"text": "The limit is 3 mmHg.\n\nSources: NASA-STD-3001 · V2 6004"})

    assert tts.spoken == ["The limit is 3 millimeters of mercury."]


def test_without_a_voice_service_it_says_so_with_503_and_the_text_stays_on_screen() -> None:
    response = client(NullTextToSpeech()).post(URL, json={"text": "hello"})

    assert response.status_code == 503


def test_a_voice_service_that_fails_is_503_not_a_crash() -> None:
    assert client(FakeTts(fail=True)).post(URL, json={"text": "hello"}).status_code == 503


def test_text_with_nothing_to_read_is_400() -> None:
    tts = FakeTts()

    response = client(tts).post(URL, json={"text": "\n\nSources: X"})

    assert response.status_code == 400
    assert tts.spoken == []


def test_a_missing_or_huge_text_is_rejected() -> None:
    web = client(FakeTts())

    assert web.post(URL, json={}).status_code == 422
    assert web.post(URL, json={"text": "x" * 20_001}).status_code == 422
