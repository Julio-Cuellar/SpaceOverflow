"""Adaptadores en memoria para pruebas y para el perfil sin base de datos (adaptador nulo)."""

from __future__ import annotations

from uuid import UUID

from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.knowledge.domain.model import Recommendation


class InMemoryRecommendations:
    def __init__(self) -> None:
        self._items: dict[UUID, Recommendation] = {}

    def save(self, recommendation: Recommendation) -> None:
        self._items[recommendation.id] = recommendation

    def all(self) -> list[Recommendation]:
        return list(self._items.values())


class InMemoryInbox:
    def __init__(self) -> None:
        self._seen: set[tuple[str, UUID]] = set()

    def mark_once(self, consumer: str, event_id: UUID) -> bool:
        key = (consumer, event_id)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True

    def is_marked(self, consumer: str, event_id: UUID) -> bool:
        return (consumer, event_id) in self._seen


class ListPublisher:
    def __init__(self) -> None:
        self.events: list[RecommendationReady] = []

    def publish(self, event: RecommendationReady) -> None:
        self.events.append(event)
