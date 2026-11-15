"""Eventos públicos de Conocimiento (dueño: Dev B)."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation


class RecommendationReady(EventPayload):
    event_type: ClassVar[str] = "knowledge.recommendation_ready"
    alert_id: UUID
    recommendation_id: UUID
    action_keys: list[str]
    citations: list[Citation]


class RecommendationEnriched(EventPayload):
    event_type: ClassVar[str] = "knowledge.recommendation_enriched"
    recommendation_id: UUID
    text: str


EVENTS = {m.event_type: m for m in (RecommendationReady, RecommendationEnriched)}
