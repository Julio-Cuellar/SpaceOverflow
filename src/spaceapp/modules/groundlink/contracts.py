"""Eventos públicos del Enlace con Tierra."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from spaceapp.platform.events import EventPayload


class PlanChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    change: Literal["NEW", "UPDATE", "CANCEL"]
    kind: Literal["SALUD", "NAVE"] | None = None
    title: str | None = None
    recurrence: str | None = None
    zone_code: str | None = None
    target_template_id: UUID | None = None


class LinkStateChanged(EventPayload):
    event_type: ClassVar[str] = "groundlink.link_state_changed"
    state: Literal["UP", "DOWN", "DEGRADED"]
    since: datetime
    queued: int


class BatchAcknowledged(EventPayload):
    event_type: ClassVar[str] = "groundlink.batch_acknowledged"
    batch_id: UUID
    items: int
    acked_at: datetime


class GroundPlanReceived(EventPayload):
    event_type: ClassVar[str] = "groundlink.ground_plan_received"
    batch_id: UUID
    plan_version: int
    changes: list[PlanChange]


EVENTS = {m.event_type: m for m in (LinkStateChanged, BatchAcknowledged, GroundPlanReceived)}
