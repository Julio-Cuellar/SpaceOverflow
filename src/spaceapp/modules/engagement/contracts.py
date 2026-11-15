"""Public events of Missions and tasks."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from spaceapp.platform.events import EventPayload

TaskKind = Literal["HEALTH", "SHIP", "INCIDENT"]
TaskOrigin = Literal["GROUND", "SYSTEM", "CREW"]


class RejectedItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    reason: str


class TaskAssigned(EventPayload):
    event_type: ClassVar[str] = "engagement.task_assigned"
    task_id: UUID
    crew_member_id: UUID
    kind: TaskKind
    origin: TaskOrigin
    action_key: str | None = None
    due_at: datetime


class TaskCompleted(EventPayload):
    event_type: ClassVar[str] = "engagement.task_completed"
    task_id: UUID
    action_key: str | None = None
    effective: bool | None = None


class TaskCreated(EventPayload):
    event_type: ClassVar[str] = "engagement.task_created"
    task_id: UUID
    kind: TaskKind
    title: str
    zone_id: UUID | None = None
    origin: TaskOrigin


class TaskBlocked(EventPayload):
    event_type: ClassVar[str] = "engagement.task_blocked"
    task_id: UUID
    origin: TaskOrigin
    reason: str


class GroundPlanApplied(EventPayload):
    event_type: ClassVar[str] = "engagement.ground_plan_applied"
    plan_version: int
    applied: list[UUID]
    rejected: list[RejectedItem]


EVENTS = {
    m.event_type: m
    for m in (TaskAssigned, TaskCompleted, TaskCreated, TaskBlocked, GroundPlanApplied)
}
