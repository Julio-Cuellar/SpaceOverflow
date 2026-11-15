"""Entities and values of the knowledge module. No external dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class EvidenceState(StrEnum):
    VERIFIED = "VERIFIED"
    TB = "TB"
    DEMO = "DEMO"
    UNVERIFIED = "UNVERIFIED"


class UnknownRuleError(LookupError):
    """The alert carries a rule the catalog does not know. The event is not marked as processed."""


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
    """What the catalog says about a rule: text, actions and citations."""

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
