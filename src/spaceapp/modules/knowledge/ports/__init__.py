"""Puertos del módulo knowledge: lo que el núcleo necesita del exterior."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from spaceapp.modules.knowledge.domain.model import Action, Citation, Guidance, Recommendation


class PassageSource(Protocol):
    """Lo mínimo para responder preguntas: pasajes citables, o vacío si ninguno es relevante."""

    def search(self, text: str, k: int) -> list[Citation]: ...


class KnowledgeSource(Protocol):
    def guidance_for(self, rule_key: str) -> Guidance: ...

    def action(self, key: str) -> Action | None: ...

    def search(self, text: str, k: int) -> list[Citation]: ...


class RecommendationRepository(Protocol):
    def save(self, recommendation: Recommendation) -> None: ...


class Inbox(Protocol):
    """Idempotencia por (consumidor, event_id). En I1 la sustituye el inbox de la plataforma."""

    def mark_once(self, consumer: str, event_id: UUID) -> bool: ...

    def is_marked(self, consumer: str, event_id: UUID) -> bool: ...
