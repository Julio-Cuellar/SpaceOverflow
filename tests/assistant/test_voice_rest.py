"""Rutas REST de la voz: audio crudo dentro, texto editable fuera, y nada se pregunta sin confirmar."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spaceapp.modules.assistant.adapters.inbound.voice_rest import build_voice_router
from spaceapp.modules.assistant.adapters.outbound.audio_store import LocalAudioStore
from spaceapp.modules.assistant.adapters.outbound.memory import (
    InMemoryConversations,
    InMemoryUtterances,
    ListPublisher,
)
from spaceapp.modules.assistant.adapters.outbound.null_llm import NullLlmGateway
from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.application.ask import AskAssistant
from spaceapp.modules.assistant.application.voice import ConfirmUtterance, SubmitAudio
from spaceapp.modules.assistant.domain.voice import Transcript
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
CONVERSATION = str(uuid.uuid4())
URL = "/api/v1/voice/utterances"


class FakeStt:
    available = True

    def __init__(self, text: str = "why do I have a headache", fail: bool = False) -> None:
        self._text = text
        self._fail = fail

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        if self._fail:
            raise RuntimeError("model down")
        return Transcript(text=self._text, confidence=0.8, language="en")


class NoAlerts:
    def titles(self) -> list[str]:
        return []


class Rig:
    def __init__(self, tmp_path: Path, stt: object) -> None:
        self.conversations = InMemoryConversations()
        utterances = InMemoryUtterances()
        ask = AskAssistant(
            passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
            llm=NullLlmGateway(),
            conversations=self.conversations,
            alerts=NoAlerts(),
            publisher=ListPublisher(),
        )
        app = FastAPI()
        app.include_router(
            build_voice_router(
                submit=SubmitAudio(
                    stt=stt,  # type: ignore[arg-type]
                    store=LocalAudioStore(tmp_path / "audio"),
                    utterances=utterances,
                ),
                confirm=ConfirmUtterance(utterances=utterances, ask=ask),
                utterances=utterances,
            )
        )
        self.client = TestClient(app)

    def upload(self, content_type: str = "audio/webm;codecs=opus", body: bytes = b"audio") -> str:
        response = self.client.post(
            f"{URL}?conversation_id={CONVERSATION}",
            content=body,
            headers={"Content-Type": content_type},
        )
        assert response.status_code == 202, response.text
        return str(response.json()["utterance_id"])


def test_uploading_audio_answers_202_and_the_transcript_waits_for_confirmation(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path, FakeStt())

    utterance_id = rig.upload()
    state = rig.client.get(f"{URL}/{utterance_id}").json()

    assert state["status"] == "TRANSCRIBED"
    assert state["text"] == "why do I have a headache"
    assert state["confidence"] == 0.8
    assert rig.conversations.messages(uuid.UUID(CONVERSATION)) == []  # nada se preguntó aún


def test_without_a_speech_model_the_state_says_to_type_the_question(tmp_path: Path) -> None:
    rig = Rig(tmp_path, NullSpeechToText())

    state = rig.client.get(f"{URL}/{rig.upload()}").json()

    assert state["status"] == "NO_TRANSCRIPT"
    assert "escribe" in state["reason"]


def test_a_failing_model_also_leaves_the_text_box_open(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt(fail=True))

    assert rig.client.get(f"{URL}/{rig.upload()}").json()["status"] == "NO_TRANSCRIPT"


@pytest.mark.parametrize("content_type", ["audio/mpeg", "text/plain", ""])
def test_an_unsupported_audio_type_is_415(tmp_path: Path, content_type: str) -> None:
    response = Rig(tmp_path, FakeStt()).client.post(
        f"{URL}?conversation_id={CONVERSATION}",
        content=b"x",
        headers={"Content-Type": content_type},
    )

    assert response.status_code == 415


def test_an_empty_upload_is_400(tmp_path: Path) -> None:
    response = Rig(tmp_path, FakeStt()).client.post(
        f"{URL}?conversation_id={CONVERSATION}", content=b"", headers={"Content-Type": "audio/wav"}
    )

    assert response.status_code == 400


def test_the_conversation_id_is_required_and_must_be_a_uuid(tmp_path: Path) -> None:
    client = Rig(tmp_path, FakeStt()).client

    assert client.post(URL, content=b"x", headers={"Content-Type": "audio/wav"}).status_code == 422
    bad = client.post(
        f"{URL}?conversation_id=nope", content=b"x", headers={"Content-Type": "audio/wav"}
    )
    assert bad.status_code == 422


def test_an_unknown_utterance_is_404(tmp_path: Path) -> None:
    client = Rig(tmp_path, FakeStt()).client
    unknown = uuid.uuid4()

    assert client.get(f"{URL}/{unknown}").status_code == 404
    assert client.post(f"{URL}/{unknown}/confirm", json={"text": "x"}).status_code == 404
    assert client.post(f"{URL}/{unknown}/discard").status_code == 404


def test_confirming_the_edited_text_asks_the_assistant_and_returns_the_answer(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path, FakeStt("the wrong words"))
    utterance_id = rig.upload()

    response = rig.client.post(
        f"{URL}/{utterance_id}/confirm", json={"text": "¿Por qué me duele la cabeza?"}
    )

    body = response.json()
    assert response.status_code == 200
    assert body["outcome"] == "ANSWERED"
    assert body["citations"]
    assert rig.client.get(f"{URL}/{utterance_id}").json()["status"] in {
        "ANSWERED",
        "TEMPLATE_ANSWER",
    }


def test_confirming_twice_is_a_conflict(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt())
    utterance_id = rig.upload()
    rig.client.post(f"{URL}/{utterance_id}/confirm", json={"text": "headache"})

    assert rig.client.post(f"{URL}/{utterance_id}/confirm", json={"text": "x"}).status_code == 409


def test_discarding_drops_the_transcript_without_asking_anything(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt())
    utterance_id = rig.upload()

    response = rig.client.post(f"{URL}/{utterance_id}/discard")

    assert response.status_code == 200
    assert response.json()["status"] == "DISCARDED"
    assert rig.conversations.messages(uuid.UUID(CONVERSATION)) == []
    assert rig.client.post(f"{URL}/{utterance_id}/discard").status_code == 409


def test_the_audio_does_not_stay_on_disk_after_the_upload(tmp_path: Path) -> None:
    rig = Rig(tmp_path, FakeStt())

    rig.upload()

    assert list((tmp_path / "audio").glob("*")) == []
