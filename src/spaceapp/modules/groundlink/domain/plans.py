"""Planes de Tierra: integridad, versiones y etapas en el enlace (13.11). Sin E/S."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

# Canalización de un plan publicado, tal como la ve Tierra.
STAGES = ("BORRADOR", "EN_COLA", "EN_EL_ENLACE", "RECIBIDO", "APLICADO", "CONFIRMADO", "RECHAZADO")
_IN_FLIGHT = {"EN_COLA", "EN_EL_ENLACE", "RECIBIDO", "APLICADO"}

Decision = Literal["received", "ignored", "rejected"]


def plan_hash(plan_version: int, items: Sequence[Mapping[str, Any]]) -> str:
    """SHA-256 del JSON canónico de versión e ítems (claves ordenadas, sin espacios)."""
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
    """Plan corrupto: se rechaza completo. Versión menor o repetida: se ignora."""
    if plan_hash(plan_version, items) != received_hash:
        return "rejected", "falla la integridad: el hash no coincide con el contenido del plan"
    if last_version is not None and plan_version <= last_version:
        return "ignored", None
    return "received", None


def in_flight(stage: str) -> bool:
    return stage in _IN_FLIGHT


@dataclass(frozen=True)
class ShipTemplate:
    """Plantilla de Tierra activa en la nave, con el estado de su última tarea."""

    id: UUID
    title: str
    kind: str
    status: str  # APLICADA, COMPLETADA o BLOQUEADA
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
    """Lo que ve Tierra al editar: las activas (marcadas si se cancelan) y las nuevas."""
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
        ShownTemplate(i.template_id, i.title or "", i.kind or "SALUD", "PENDIENTE", None, False)
        for i in items
        if i.change == "NEW"
    ]
    return shown
