"""Servidor de desarrollo del asistente: n8n, Ollama y las herramientas del agente sin `main.py`.

Es composición, no un módulo: aquí sí se pueden juntar adaptadores de Conocimiento y Asistente.
No es el servidor de la entrega (ese es el de Dev A) ni tiene autenticación: escucha en local.

    python -m spaceapp.devtools.assistant_server        # puerto 8000
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, StringConstraints

from spaceapp.modules.assistant.adapters.inbound.rest import build_router
from spaceapp.modules.assistant.adapters.inbound.voice_rest import build_voice_router
from spaceapp.modules.assistant.adapters.outbound.audio_store import LocalAudioStore
from spaceapp.modules.assistant.adapters.outbound.http_stt import HttpSpeechToText
from spaceapp.modules.assistant.adapters.outbound.memory import (
    InMemoryConversations,
    InMemoryUtterances,
    ListPublisher,
)
from spaceapp.modules.assistant.adapters.outbound.n8n import N8nOrchestrator
from spaceapp.modules.assistant.adapters.outbound.null_llm import NullLlmGateway
from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.application.ask import AskAssistant
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog
from spaceapp.modules.assistant.application.voice import ConfirmUtterance, SubmitAudio
from spaceapp.modules.assistant.ports import AssistantOrchestrator, PassageSearch, SpeechToText
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.hybrid_source import build_knowledge_source
from spaceapp.modules.knowledge.adapters.outbound.ollama_embedder import DEFAULT_URL, OllamaEmbedder
from spaceapp.modules.knowledge.adapters.outbound.rag_source import FallbackKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

ROOT = Path(__file__).resolve().parents[3]
WHISPER_URL = "http://127.0.0.1:9000"
DEFAULT_WEBHOOK = "http://127.0.0.1:5678/webhook/space-apps-assistant"


class NoAlerts:
    """Sin alertas activas: el servidor de desarrollo no tiene Monitoreo."""

    def titles(self) -> list[str]:
        return []


class AskRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def build_app(
    *,
    passages: PassageSearch,
    orchestrator: AssistantOrchestrator | None,
    retrievals: RetrievalLog | None = None,
    orchestrator_timeout_s: float = 120.0,
    speech: SpeechToText | None = None,
    audio_dir: Path | None = None,
) -> FastAPI:
    log = retrievals or RetrievalLog()
    utterances = InMemoryUtterances()
    ask = AskAssistant(
        passages=passages,
        llm=NullLlmGateway(),
        conversations=InMemoryConversations(),
        alerts=NoAlerts(),
        publisher=ListPublisher(),
        orchestrator=orchestrator,
        retrievals=log,
        orchestrator_timeout_s=orchestrator_timeout_s,
    )
    confirm = ConfirmUtterance(utterances=utterances, ask=ask)

    app = FastAPI(title="Asistente (desarrollo)")
    app.include_router(build_router(log=log, passages=passages, alerts=NoAlerts()))
    app.include_router(
        build_voice_router(
            submit=SubmitAudio(
                stt=speech or NullSpeechToText(),
                store=LocalAudioStore(audio_dir or ROOT / "data" / "voice" / "incoming"),
                utterances=utterances,
            ),
            confirm=confirm,
            utterances=utterances,
        )
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/dev/ask")
    def dev_ask(request: AskRequest) -> dict[str, object]:
        from uuid import uuid4

        result = confirm.confirm_text(uuid4(), request.text)
        turn = utterances.all()[-1]
        return {
            "state": turn.status.value,
            "outcome": result.outcome.value,
            "text": result.text,
            "composed_by": result.composed_by,
            "degraded": result.degraded,
            "citations": [c.model_dump() for c in result.citations],
        }

    return app


def _knowledge() -> KnowledgeQuery:
    demo = DemoKnowledgeSource.from_file(ROOT / "data" / "knowledge" / "demo_catalog.json")
    index = ROOT / "data" / "knowledge" / "index" / "chunks.jsonl"
    glossary = ROOT / "data" / "knowledge" / "glossary_es_en.json"
    if index.exists():
        # Híbrida (palabras y significado) si hay vectores y el modelo de embeddings; si no, o si
        # Ollama no responde, solo palabras.
        embedder = OllamaEmbedder(base_url=os.environ.get("SPACEAPP_OLLAMA_URL", DEFAULT_URL))
        rag = build_knowledge_source(index, glossary, embedder)
        return KnowledgeQuery(FallbackKnowledgeSource(rag, demo))
    return KnowledgeQuery(demo)


def main() -> None:
    webhook = os.environ.get("SPACEAPP_N8N_WEBHOOK", DEFAULT_WEBHOOK)
    timeout = float(os.environ.get("SPACEAPP_ORCHESTRATOR_TIMEOUT_S", "120"))
    app = build_app(
        passages=_knowledge(),
        orchestrator=N8nOrchestrator(webhook, timeout_s=timeout),
        orchestrator_timeout_s=timeout,
        speech=HttpSpeechToText(os.environ.get("SPACEAPP_WHISPER_URL", WHISPER_URL)),
    )
    uvicorn.run(app, host=os.environ.get("SPACEAPP_DEV_HOST", "0.0.0.0"), port=8000)


if __name__ == "__main__":
    main()
