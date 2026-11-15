"""HTTP server of the Whisper container. A fake model, a real server on port 0."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from spaceapp.devtools.voice_server import MAX_AUDIO_BYTES, build_server
from spaceapp.modules.assistant.domain.voice import Transcript


class FakeStt:
    available = True

    def __init__(self, transcript: Transcript | None, fail: bool = False) -> None:
        self._transcript = transcript
        self._fail = fail
        self.calls: list[tuple[bytes, str]] = []

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        self.calls.append((audio, content_type))
        if self._fail:
            raise RuntimeError("model exploded")
        return self._transcript


@pytest.fixture
def serve() -> Iterator[Any]:
    servers: list[ThreadingHTTPServer] = []

    def start(stt: FakeStt, tts: object | None = None) -> str:
        server = build_server(stt, host="127.0.0.1", port=0, tts=tts)  # type: ignore[arg-type]
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


class FakeTts:
    available = True

    def __init__(self, audio: bytes | None = b"RIFFfake-wav", fail: bool = False) -> None:
        self._audio = audio
        self._fail = fail
        self.spoken: list[str] = []

    def speak(self, text: str) -> bytes | None:
        self.spoken.append(text)
        if self._fail:
            raise RuntimeError("voice model exploded")
        return self._audio


def speak(url: str, payload: Any) -> tuple[int, str, bytes]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers["Content-Type"], response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers["Content-Type"], error.read()


def post(url: str, body: bytes, content_type: str = "audio/webm") -> tuple[int, Any]:
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": content_type}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_health_answers_without_loading_the_model(serve: Any) -> None:
    base = serve(FakeStt(None))

    with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
        assert json.load(response) == {"status": "ok"}


def test_it_transcribes_the_audio_it_receives(serve: Any) -> None:
    stt = FakeStt(Transcript("what is the cabin pressure", 0.9, "en"))
    base = serve(stt)

    status, body = post(f"{base}/transcribe", b"audio-bytes", "audio/webm;codecs=opus")

    assert status == 200
    assert body == {"text": "what is the cabin pressure", "confidence": 0.9, "language": "en"}
    assert stt.calls == [(b"audio-bytes", "audio/webm;codecs=opus")]


def test_no_speech_is_an_empty_text_not_an_error(serve: Any) -> None:
    status, body = post(f"{serve(FakeStt(None))}/transcribe", b"silence")

    assert status == 200
    assert body["text"] == ""


def test_an_empty_body_is_a_bad_request(serve: Any) -> None:
    status, body = post(f"{serve(FakeStt(None))}/transcribe", b"")

    assert status == 400
    assert "error" in body


def test_a_body_over_the_limit_is_refused_without_reading_it(serve: Any) -> None:
    stt = FakeStt(Transcript("x", None, "en"))
    base = serve(stt)
    request = urllib.request.Request(
        f"{base}/transcribe",
        data=b"x",
        headers={"Content-Length": str(MAX_AUDIO_BYTES + 1), "Content-Type": "audio/wav"},
        method="POST",
    )

    with pytest.raises((urllib.error.HTTPError, urllib.error.URLError, ConnectionError)):
        urllib.request.urlopen(request, timeout=5)

    assert stt.calls == []


def test_a_model_failure_is_a_json_error_not_a_crash(serve: Any) -> None:
    status, body = post(f"{serve(FakeStt(None, fail=True))}/transcribe", b"audio")

    assert status == 500
    assert "error" in body


def test_an_unknown_path_is_not_found(serve: Any) -> None:
    status, _ = post(f"{serve(FakeStt(None))}/other", b"audio")

    assert status == 404


def test_speak_turns_the_text_into_a_wav(serve: Any) -> None:
    tts = FakeTts()
    base = serve(FakeStt(None), tts)

    status, content_type, audio = speak(f"{base}/speak", {"text": "The limit is three."})

    assert status == 200
    assert content_type == "audio/wav"
    assert audio == b"RIFFfake-wav"
    assert tts.spoken == ["The limit is three."]


def test_speak_without_a_voice_model_is_503_and_json(serve: Any) -> None:
    status, content_type, body = speak(f"{serve(FakeStt(None))}/speak", {"text": "hello"})

    assert status == 503
    assert content_type == "application/json"
    assert "error" in json.loads(body)


def test_speak_with_an_unavailable_voice_is_503(serve: Any) -> None:
    status, _, _ = speak(f"{serve(FakeStt(None), FakeTts(audio=None))}/speak", {"text": "hello"})

    assert status == 503


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "   "}, {"text": 5}, ["x"]])
def test_speak_rejects_a_missing_or_empty_text(serve: Any, payload: Any) -> None:
    tts = FakeTts()

    status, _, _ = speak(f"{serve(FakeStt(None), tts)}/speak", payload)

    assert status == 400
    assert tts.spoken == []


def test_speak_with_a_failing_model_is_a_json_error(serve: Any) -> None:
    status, content_type, _ = speak(
        f"{serve(FakeStt(None), FakeTts(fail=True))}/speak", {"text": "hi"}
    )

    assert status == 500
    assert content_type == "application/json"
