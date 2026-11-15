"""Public events of Knowledge. Other modules may only import this and the facade."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation

# The citation belongs to the shared kernel (`platform/vocab`): a single definition for all
# modules. The alias keeps the name the assistant uses it with.
CitationDTO = Citation


class RecommendationReady(EventPayload):
    """`knowledge.recommendation_ready`: the template is ready, without waiting for any model."""

    event_type: ClassVar[str] = "knowledge.recommendation_ready"
    alert_id: UUID
    recommendation_id: UUID
    action_keys: list[str]
    citations: list[Citation]


class RecommendationEnriched(EventPayload):
    """`knowledge.recommendation_enriched`: the same recommendation written by the local model."""

    event_type: ClassVar[str] = "knowledge.recommendation_enriched"
    recommendation_id: UUID
    text: str


EVENTS = {m.event_type: m for m in (RecommendationReady, RecommendationEnriched)}
