"""What to do with each item of a Ground plan (13.11). An invalid item is rejected on its own."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from spaceapp.modules.engagement.domain.tasks import CREW_KINDS, RECURRENCES


@dataclass(frozen=True)
class PlanItem:
    change: str  # NEW, UPDATE, CANCEL
    kind: str | None
    title: str | None
    recurrence: str | None
    zone_code: str | None
    target_template_id: UUID | None


@dataclass(frozen=True)
class TemplateState:
    id: UUID
    origin: str
    active: bool


@dataclass(frozen=True)
class PlanAction:
    change: str
    template_id: UUID
    kind: str | None
    title: str | None
    recurrence: str | None
    zone_code: str | None


@dataclass(frozen=True)
class Rejection:
    title: str
    reason: str


def _fields(item: PlanItem, zones: set[str], *, required: bool) -> str | None:
    if required and item.kind is None:
        return "missing kind"
    if item.kind is not None and item.kind not in CREW_KINDS:
        return f"invalid kind {item.kind!r}: Ground schedules HEALTH or SHIP tasks"
    if item.title is not None and not item.title.strip():
        return "the title is empty"
    if required and item.title is None:
        return "missing title"
    if item.recurrence is not None and item.recurrence not in RECURRENCES:
        return f"unknown recurrence {item.recurrence!r}"
    if item.zone_code is not None and item.zone_code not in zones:
        return f"nonexistent zone {item.zone_code!r}"
    return None


def plan_actions(
    items: Sequence[PlanItem], templates: Mapping[UUID, TemplateState], zones: set[str]
) -> tuple[list[PlanAction], list[Rejection]]:
    actions: list[PlanAction] = []
    rejected: list[Rejection] = []

    def reject(item: PlanItem, reason: str) -> None:
        rejected.append(Rejection(item.title or str(item.target_template_id or "?"), reason))

    for item in items:
        target = templates.get(item.target_template_id) if item.target_template_id else None
        if item.change == "NEW":
            if target is not None:
                reject(item, "the template already exists")
                continue
            error = _fields(item, zones, required=True)
            if error:
                reject(item, error)
                continue
            actions.append(
                PlanAction(
                    "NEW",
                    item.target_template_id or uuid4(),
                    item.kind,
                    (item.title or "").strip(),
                    item.recurrence or "DAILY",
                    item.zone_code,
                )
            )
        elif item.change in ("UPDATE", "CANCEL"):
            if target is None:
                reject(item, "the template does not exist on the ship")
                continue
            if target.origin != "GROUND":
                reject(item, "Ground only changes its own templates: local tasks prevail")
                continue
            error = _fields(item, zones, required=False) if item.change == "UPDATE" else None
            if error:
                reject(item, error)
                continue
            title = item.title.strip() if item.title else None
            actions.append(
                PlanAction(
                    item.change, target.id, item.kind, title, item.recurrence, item.zone_code
                )
            )
        else:
            reject(item, f"unknown change {item.change!r}")
    return actions, rejected
