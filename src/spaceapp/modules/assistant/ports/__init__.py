"""Assistant ports: what it needs from the outside. Reads go through public facades."""

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
    """Writes with a model, only from what was retrieved. `available` is False in the null one."""

    available: bool

    def stream(
        self, question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]
    ) -> Iterator[str]: ...


class PassageSearch(Protocol):
    def search(self, text: str, k: int) -> list[CitationDTO]: ...


class ActiveAlerts(Protocol):
    """Read-only. The assistant may name an active alert, never change it."""

    def titles(self) -> list[str]: ...


class ConversationRepository(Protocol):
    def add(
        self, conversation_id: UUID, role: str, text: str, citations: tuple[CitationDTO, ...]
    ) -> UUID:
        """Stores a message and returns its id (the event's `utterance_id`)."""
        ...

    def messages(self, conversation_id: UUID) -> list[StoredMessage]: ...


class EventPublisher(Protocol):
    """Publishes via the outbox (in memory until I1). It does not block the astronaut's answer."""

    def publish(self, event: AnswerReady) -> None: ...


class SpeechToText(Protocol):
    """Speech to text. `available` is False in the null adapter: then the question is typed."""

    available: bool

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None: ...


class TextToSpeech(Protocol):
    """Text to speech. `available` is False in the null adapter: then the answer is only read."""

    available: bool

    def speak(self, text: str) -> bytes | None:
        """WAV audio of the text. Raises if the voice service does not answer."""
        ...


class AudioStore(Protocol):
    def save(self, utterance_id: UUID, audio: bytes, extension: str) -> str:
        """Stores the audio and returns where it ended up."""
        ...

    def delete(self, path: str) -> None:
        """Deletes the audio; if it is no longer there, it does nothing."""
        ...


class UtteranceRepository(Protocol):
    def add(self, utterance: Utterance) -> None: ...

    def get(self, utterance_id: UUID) -> Utterance:
        """Lanza `UnknownUtteranceError` si no existe."""
        ...

    def update(self, utterance: Utterance) -> None: ...


class AssistantOrchestrator(Protocol):
    """Whoever answers with tools (n8n). It returns text only: the backend adds the citations.

    Raises `OrchestratorError` if it fails. `available` is False if it is not configured.
    """

    @property
    def available(self) -> bool: ...

    def answer(
        self, turn_id: UUID, conversation_id: UUID, question: str, alerts: Sequence[str]
    ) -> str: ...
