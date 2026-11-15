"""Servidor de desarrollo del asistente: solo para probar n8n y Ollama sin el main.py de Dev A."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from test_ask_with_orchestrator import FakeAgent

from spaceapp.devtools.assistant_server import build_app
from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
HEADACHE = "¿Por qué me duele la cabeza?"


def client(**agent_options: object) -> TestClient:
    log = RetrievalLog()
    app = build_app(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        orchestrator=FakeAgent(log, **agent_options),  # type: ignore[arg-type]
        retrievals=log,
    )
    return TestClient(app)


def test_it_reports_it_is_alive() -> None:
    assert client().get("/health").json() == {"status": "ok"}


def test_a_question_goes_through_the_state_machine_and_is_answered_with_citations() -> None:
    response = client().post("/dev/ask", json={"text": HEADACHE})

    body = response.json()
    assert response.status_code == 200
    assert body["state"] == "ANSWERED"
    assert body["composed_by"] == "n8n"
    assert body["degraded"] is False
    assert body["citations"]


def test_a_question_without_a_source_closes_as_no_info() -> None:
    body = client(text="Es París.").post("/dev/ask", json={"text": "¿Capital de Francia?"}).json()

    assert body["state"] == "NO_INFO"
    assert body["citations"] == []
    assert "París" not in body["text"]


def test_a_failing_orchestrator_closes_as_a_template_answer() -> None:
    body = client(fail=True).post("/dev/ask", json={"text": HEADACHE}).json()

    assert body["state"] == "TEMPLATE_ANSWER"
    assert body["degraded"] is True


def test_an_empty_question_is_rejected() -> None:
    assert client().post("/dev/ask", json={"text": "  "}).status_code == 422


def test_the_agent_tools_are_mounted_and_refuse_a_turn_that_is_not_open() -> None:
    response = client().post(
        f"/api/v1/assistant/tools/{uuid.uuid4()}/search_passages", json={"query": "cabeza"}
    )

    assert response.status_code == 404


class FakeVoice:
    available = True

    def transcribe(self, audio: bytes, content_type: str) -> object:
        from spaceapp.modules.assistant.domain.voice import Transcript

        # El catálogo de demostración está en español: la pregunta debe coincidir con él.
        return Transcript(HEADACHE, 0.9, "en")


def voice_client(tmp_path: Path, speech: object | None = None) -> TestClient:
    log = RetrievalLog()
    app = build_app(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        orchestrator=FakeAgent(log),  # type: ignore[arg-type]
        retrievals=log,
        speech=speech if speech is not None else FakeVoice(),  # type: ignore[arg-type]
        audio_dir=tmp_path,
    )
    return TestClient(app)


def test_the_voice_routes_are_served_and_a_spoken_question_is_answered_after_confirming(
    tmp_path: Path,
) -> None:
    web = voice_client(tmp_path)
    conversation = uuid.uuid4()

    uploaded = web.post(
        f"/api/v1/voice/utterances?conversation_id={conversation}",
        content=b"audio",
        headers={"Content-Type": "audio/webm"},
    )
    utterance_id = uploaded.json()["utterance_id"]
    transcript = web.get(f"/api/v1/voice/utterances/{utterance_id}").json()
    answer = web.post(
        f"/api/v1/voice/utterances/{utterance_id}/confirm", json={"text": transcript["text"]}
    ).json()

    assert uploaded.status_code == 202
    assert transcript["status"] == "TRANSCRIBED"
    assert answer["outcome"] == "ANSWERED"


def test_without_a_speech_service_the_server_still_works_and_voice_says_to_type(
    tmp_path: Path,
) -> None:
    web = voice_client(tmp_path, speech=NullSpeechToText())
    uploaded = web.post(
        f"/api/v1/voice/utterances?conversation_id={uuid.uuid4()}",
        content=b"audio",
        headers={"Content-Type": "audio/webm"},
    )

    state = web.get(f"/api/v1/voice/utterances/{uploaded.json()['utterance_id']}").json()
    assert state["status"] == "NO_TRANSCRIPT"
