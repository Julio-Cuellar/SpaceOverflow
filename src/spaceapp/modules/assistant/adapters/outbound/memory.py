"""In-memory conversation repository. Used for tests and for the demo without a database."""

from __future__ import annotations

from uuid import UUID, uuid4

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.assistant.ports import StoredMessage
from spaceapp.modules.knowledge.contracts import CitationDTO


class InMemoryConversations:
    def __init__(self) -> None:
        self._messages: dict[UUID, list[StoredMessage]] = {}

    def add(
        self, conversation_id: UUID, role: str, text: str, citations: tuple[CitationDTO, ...]
    ) -> UUID:
        message_id = uuid4()
        self._messages.setdefault(conversation_id, []).append(
            StoredMessage(
                id=message_id,
                conversation_id=conversation_id,
                role=role,
                text=text,
                citations=citations,
            )
        )
        return message_id

    def messages(self, conversation_id: UUID) -> list[StoredMessage]:
        return list(self._messages.get(conversation_id, []))


class ListPublisher:
    """In-memory publisher: stores the events. In I1 the real outbox replaces it."""

    def __init__(self) -> None:
        self.events: list[AnswerReady] = []

    def publish(self, event: AnswerReady) -> None:
        self.events.append(event)
