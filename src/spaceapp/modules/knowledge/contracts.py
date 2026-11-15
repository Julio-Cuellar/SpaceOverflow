"""Eventos públicos de Conocimiento. Otros módulos solo pueden importar esto y la fachada."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation

# La cita es del kernel compartido (`platform/vocab`): una sola definición para todos los módulos.
# El alias conserva el nombre con el que la usa el asistente.
CitationDTO = Citation


class RecommendationReady(EventPayload):
    """`knowledge.recommendation_ready`: la plantilla ya está lista, sin esperar a ningún modelo."""

    event_type: ClassVar[str] = "knowledge.recommendation_ready"
    alert_id: UUID
    recommendation_id: UUID
    action_keys: list[str]
    citations: list[Citation]


class RecommendationEnriched(EventPayload):
    """`knowledge.recommendation_enriched`: la misma recomendación redactada por el modelo local."""

    event_type: ClassVar[str] = "knowledge.recommendation_enriched"
    recommendation_id: UUID
    text: str


EVENTS = {m.event_type: m for m in (RecommendationReady, RecommendationEnriched)}
