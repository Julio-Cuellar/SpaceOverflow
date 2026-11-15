"""Eventos públicos del Asistente (dueño: Dev B)."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation


class AnswerReady(EventPayload):
    event_type: ClassVar[str] = "assistant.answer_ready"
    utterance_id: UUID
    text: str
    citations: list[Citation]


EVENTS = {m.event_type: m for m in (AnswerReady,)}
