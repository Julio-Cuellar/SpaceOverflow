"""Entidades y valores del módulo knowledge. Sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class EvidenceState(StrEnum):
    VERIFICADO = "VERIFICADO"
    TB = "TB"
    DEMO = "DEMO"
    NO_VERIFICADO = "NO_VERIFICADO"


class UnknownRuleError(LookupError):
    """La alerta trae una regla que el catálogo no conoce. No se marca el evento como procesado."""


@dataclass(frozen=True)
class Action:
    key: str
    title: str
    description: str


@dataclass(frozen=True)
class Citation:
    document_code: str
    requirement_ref: str | None
    page: int | None
    excerpt: str
    evidence_state: EvidenceState


@dataclass(frozen=True)
class Guidance:
    """Lo que el catálogo dice sobre una regla: texto, acciones y citas."""

    rule_key: str
    source_kind: str
    body: str
    actions: tuple[Action, ...]
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class Recommendation:
    id: UUID
    alert_id: UUID
    rule_key: str
    source_kind: str
    body: str
    actions: tuple[Action, ...]
    citations: tuple[Citation, ...]
