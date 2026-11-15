"""Public events of the Assistant. Other modules may only import this and the facade."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation


class AnswerReady(EventPayload):
    """`assistant.answer_ready`. The gateway translates it into a WebSocket message."""

    event_type: ClassVar[str] = "assistant.answer_ready"
    utterance_id: UUID
    text: str
    citations: list[Citation]


EVENTS = {m.event_type: m for m in (AnswerReady,)}
