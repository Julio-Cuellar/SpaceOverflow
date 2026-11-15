"""Ports of the knowledge module: what the core needs from the outside."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from spaceapp.modules.knowledge.domain.model import Action, Citation, Guidance, Recommendation


class EmbeddingError(Exception):
    """The embeddings model did not answer or returned something invalid. Search goes on without."""


class Embedder(Protocol):
    """Turns texts into vectors. `model` identifies the vectors it produces."""

    model: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class PassageSource(Protocol):
    """The minimum to answer questions: citable passages, or empty if none is relevant."""

    def search(self, text: str, k: int) -> list[Citation]: ...


class KnowledgeSource(Protocol):
    def guidance_for(self, rule_key: str) -> Guidance: ...

    def action(self, key: str) -> Action | None: ...

    def search(self, text: str, k: int) -> list[Citation]: ...


class RecommendationRepository(Protocol):
    def save(self, recommendation: Recommendation) -> None: ...


class Inbox(Protocol):
    """Idempotency per (consumer, event_id). In I1 the platform's inbox replaces it."""

    def mark_once(self, consumer: str, event_id: UUID) -> bool: ...

    def is_marked(self, consumer: str, event_id: UUID) -> bool: ...
