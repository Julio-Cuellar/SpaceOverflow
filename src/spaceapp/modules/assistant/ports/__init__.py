"""Puertos del asistente: lo que necesita del exterior. Las lecturas van por fachadas públicas."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.assistant.domain.voice import Transcript, Utterance
from spaceapp.modules.knowledge.contracts import CitationDTO


@dataclass(frozen=True)
class StoredMessage:
    id: UUID
    conversation_id: UUID
    role: str
    text: str
    citations: tuple[CitationDTO, ...]


class LlmGateway(Protocol):
    """Redacta con un modelo, solo con lo recuperado. `available` es False en el adaptador nulo."""

    available: bool

    def stream(
        self, question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]
    ) -> Iterator[str]: ...


class PassageSearch(Protocol):
    def search(self, text: str, k: int) -> list[CitationDTO]: ...


class ActiveAlerts(Protocol):
    """Solo lectura. El asistente puede nombrar una alerta activa, nunca cambiarla."""

    def titles(self) -> list[str]: ...


class ConversationRepository(Protocol):
    def add(
        self, conversation_id: UUID, role: str, text: str, citations: tuple[CitationDTO, ...]
    ) -> UUID:
        """Guarda un mensaje y devuelve su id (el `utterance_id` del evento)."""
        ...

    def messages(self, conversation_id: UUID) -> list[StoredMessage]: ...


class EventPublisher(Protocol):
    """Publica por el outbox (en memoria hasta I1). No bloquea la respuesta al astronauta."""

    def publish(self, event: AnswerReady) -> None: ...


class SpeechToText(Protocol):
    """Voz a texto. `available` es False en el adaptador nulo: entonces se escribe a mano."""

    available: bool

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None: ...


class AudioStore(Protocol):
    def save(self, utterance_id: UUID, audio: bytes, extension: str) -> str:
        """Guarda el audio y devuelve dónde quedó."""
        ...


class UtteranceRepository(Protocol):
    def add(self, utterance: Utterance) -> None: ...

    def get(self, utterance_id: UUID) -> Utterance:
        """Lanza `UnknownUtteranceError` si no existe."""
        ...

    def update(self, utterance: Utterance) -> None: ...
