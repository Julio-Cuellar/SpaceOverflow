"""Eventos públicos del Asistente. Otros módulos solo pueden importar esto y la fachada."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation


class AnswerReady(EventPayload):
    """`assistant.answer_ready`. El gateway lo traduce a un mensaje de WebSocket."""

    event_type: ClassVar[str] = "assistant.answer_ready"
    utterance_id: UUID
    text: str
    citations: list[Citation]


EVENTS = {m.event_type: m for m in (AnswerReady,)}
