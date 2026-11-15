"""Eventos públicos del módulo assistant. Es lo único que otros módulos pueden importar."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from spaceapp.modules.knowledge.contracts import CitationDTO


class AnswerReady(BaseModel):
    """Payload de `assistant.answer_ready` (plan, sección 4.1). El gateway lo traduce a WS."""

    utterance_id: UUID
    text: str
    citations: list[CitationDTO]


# Provisional de la fusión: el registro de eventos de Dev A espera EVENTS. La fase 2 lo sustituye
# por los payloads reales (EventPayload) y esta prueba de contratos pasa a verde.
EVENTS: dict[str, type] = {}
