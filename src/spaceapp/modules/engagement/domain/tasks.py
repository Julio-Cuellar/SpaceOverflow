"""Tareas del día: tipos, orígenes, permisos, racha e instancias de las plantillas. Sin E/S."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

KINDS = ("SALUD", "NAVE", "INCIDENTE")
CREW_KINDS = ("SALUD", "NAVE")  # las de incidente las abre el sistema
ORIGINS = ("TIERRA", "SISTEMA", "TRIPULACION")
STATUSES = ("PENDIENTE", "COMPLETADA", "BLOQUEADA")
RECURRENCES = ("DIARIA", "UNA_VEZ")


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
    due_time: str  # HH:MM, hora de la nave (UTC)


def can_change(origin: str) -> bool:
    """Solo las tareas propias de la tripulación se editan o borran.

    Las de Tierra y las del sistema se completan, se posponen o se bloquean con motivo.
    """
    return origin == "TRIPULACION"


def check_new_task(kind: str, title: str) -> str | None:
    if kind not in CREW_KINDS:
        return "INVALID_KIND"
    if not title.strip():
        return "TITLE_REQUIRED"
    return None


def check_block(status: str, reason: str) -> str | None:
    if status == "COMPLETADA":
        return "ALREADY_COMPLETED"
    if not reason.strip():
        return "REASON_REQUIRED"
    return None


def counts_for_streak(task: TaskFacts) -> bool:
    """Solo suman las rutinas de salud completadas. Ni Tierra, ni incidentes, ni alertas (13.8)."""
    return (
        task.status == "COMPLETADA"
        and task.kind == "SALUD"
        and task.origin != "TIERRA"
        and task.source_alert_id is None
    )


def streak(tasks: Iterable[TaskFacts]) -> int:
    return sum(1 for t in tasks if counts_for_streak(t))


def due_instances(
    templates: Sequence[Template], day: date, *, today: set[UUID], ever: set[UUID]
) -> list[Template]:
    """Plantillas que necesitan su tarea del día: diarias sin tarea hoy, de una vez sin ninguna."""
    out: list[Template] = []
    for t in templates:
        if not t.active:
            continue
        daily_missing = t.recurrence == "DIARIA" and t.id not in today
        once_missing = t.recurrence == "UNA_VEZ" and t.id not in ever
        if daily_missing or once_missing:
            out.append(t)
    return out
