"""Repositorio en memoria de conversaciones. Sirve para pruebas y para la demo sin base de datos."""

from __future__ import annotations

from uuid import UUID, uuid4

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.assistant.domain.voice import UnknownUtteranceError, Utterance
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
    """Publicador en memoria: guarda los eventos. En I1 lo reemplaza el outbox real."""

    def __init__(self) -> None:
        self.events: list[AnswerReady] = []

    def publish(self, event: AnswerReady) -> None:
        self.events.append(event)


class InMemoryUtterances:
    def __init__(self) -> None:
        self._items: dict[UUID, Utterance] = {}

    def add(self, utterance: Utterance) -> None:
        self._items[utterance.id] = utterance

    def get(self, utterance_id: UUID) -> Utterance:
        try:
            return self._items[utterance_id]
        except KeyError:
            raise UnknownUtteranceError(str(utterance_id)) from None

    def update(self, utterance: Utterance) -> None:
        self.get(utterance.id)
        self._items[utterance.id] = utterance
