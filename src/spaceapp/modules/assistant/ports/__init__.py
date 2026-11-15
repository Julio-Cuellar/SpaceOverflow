"""Assistant ports: what it needs from the outside. Reads go through public facades."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.knowledge.contracts import CitationDTO


@dataclass(frozen=True)
class StoredMessage:
    id: UUID
    conversation_id: UUID
    role: str
    text: str
    citations: tuple[CitationDTO, ...]


class LlmGateway(Protocol):
    """Composes with a model, only from what was retrieved. `available` is False without one."""

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
    """Publishes through the outbox (in memory until I1). It does not block the astronaut answer."""

    def publish(self, event: AnswerReady) -> None: ...
