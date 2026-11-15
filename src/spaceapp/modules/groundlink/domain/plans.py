"""Ground plans: integrity, versions and stages on the link (13.11). No I/O."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

# Pipeline of a published plan, as Ground sees it.
STAGES = ("DRAFT", "QUEUED", "IN_TRANSIT", "RECEIVED", "APPLIED", "CONFIRMED", "REJECTED")
_IN_FLIGHT = {"QUEUED", "IN_TRANSIT", "RECEIVED", "APPLIED"}

Decision = Literal["received", "ignored", "rejected"]


def plan_hash(plan_version: int, items: Sequence[Mapping[str, Any]]) -> str:
    """SHA-256 of the canonical JSON of version and items (sorted keys, no spaces)."""
    canonical = json.dumps(
        {"plan_version": plan_version, "items": list(items)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def inbound_decision(
    plan_version: int,
    items: Sequence[Mapping[str, Any]],
    received_hash: str,
    *,
    last_version: int | None,
) -> tuple[Decision, str | None]:
    """Corrupt plan: rejected as a whole. Older or repeated version: ignored."""
    if plan_hash(plan_version, items) != received_hash:
        return "rejected", "integrity failure: the hash does not match the plan content"
    if last_version is not None and plan_version <= last_version:
        return "ignored", None
    return "received", None


def in_flight(stage: str) -> bool:
    return stage in _IN_FLIGHT


@dataclass(frozen=True)
class ShipTemplate:
    """Active Ground template on the ship, with the status of its latest task."""

    id: UUID
    title: str
    kind: str
    status: str  # APPLIED, COMPLETED or BLOCKED
    blocked_reason: str | None


@dataclass(frozen=True)
class DraftItem:
    change: str
    template_id: UUID
    title: str | None
    kind: str | None


@dataclass(frozen=True)
class ShownTemplate:
    id: UUID
    title: str
    kind: str
    status: str
    blocked_reason: str | None
    cancelled: bool


def draft_templates(
    active: Sequence[ShipTemplate], items: Sequence[DraftItem]
) -> list[ShownTemplate]:
    """What Ground sees while editing: the active ones (flagged if cancelled) and the new ones."""
    cancelled = {i.template_id for i in items if i.change == "CANCEL"}
    renamed = {i.template_id: i.title for i in items if i.change == "UPDATE" and i.title}
    shown = [
        ShownTemplate(
            t.id,
            renamed.get(t.id) or t.title,
            t.kind,
            t.status,
            t.blocked_reason,
            t.id in cancelled,
        )
        for t in active
    ]
    shown += [
        ShownTemplate(i.template_id, i.title or "", i.kind or "HEALTH", "PENDING", None, False)
        for i in items
        if i.change == "NEW"
    ]
    return shown
