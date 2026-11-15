"""Daily tasks: kinds, origins, permissions, streak and template instances. No I/O."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

KINDS = ("HEALTH", "SHIP", "INCIDENT")
CREW_KINDS = ("HEALTH", "SHIP")  # incident tasks are opened by the system
ORIGINS = ("GROUND", "SYSTEM", "CREW")
STATUSES = ("PENDING", "COMPLETED", "BLOCKED")
RECURRENCES = ("DAILY", "ONCE")


@dataclass(frozen=True)
class TaskFacts:
    kind: str
    origin: str
    status: str
    source_alert_id: UUID | None


@dataclass(frozen=True)
class Template:
    id: UUID
    kind: str
    title: str
    recurrence: str
    zone_code: str | None
    origin: str
    active: bool
    due_time: str  # HH:MM, ship time (UTC)


def can_change(origin: str) -> bool:
    """Only the crew's own tasks can be edited or deleted.

    Ground and system tasks are completed, snoozed or blocked with a reason.
    """
    return origin == "CREW"


def check_new_task(kind: str, title: str) -> str | None:
    if kind not in CREW_KINDS:
        return "INVALID_KIND"
    if not title.strip():
        return "TITLE_REQUIRED"
    return None


def check_block(status: str, reason: str) -> str | None:
    if status == "COMPLETED":
        return "ALREADY_COMPLETED"
    if not reason.strip():
        return "REASON_REQUIRED"
    return None


def counts_for_streak(task: TaskFacts) -> bool:
    """Only completed health routines count. Not Ground tasks, incidents or alerts (13.8)."""
    return (
        task.status == "COMPLETED"
        and task.kind == "HEALTH"
        and task.origin != "GROUND"
        and task.source_alert_id is None
    )


def streak(tasks: Iterable[TaskFacts]) -> int:
    return sum(1 for t in tasks if counts_for_streak(t))


def due_instances(
    templates: Sequence[Template], day: date, *, today: set[UUID], ever: set[UUID]
) -> list[Template]:
    """Templates needing their daily task: daily with none today, one-time with none ever."""
    out: list[Template] = []
    for t in templates:
        if not t.active:
            continue
        daily_missing = t.recurrence == "DAILY" and t.id not in today
        once_missing = t.recurrence == "ONCE" and t.id not in ever
        if daily_missing or once_missing:
            out.append(t)
    return out
