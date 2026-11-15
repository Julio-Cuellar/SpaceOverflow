"""Missions and tasks ports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from spaceapp.modules.engagement.domain.plans import PlanAction, TemplateState
from spaceapp.modules.engagement.domain.tasks import Template


@dataclass(frozen=True)
class NewTask:
    id: UUID
    crew_member_id: UUID
    template_id: UUID | None
    origin: str
    kind: str
    title: str
    zone_id: UUID | None
    day: date
    due_at: datetime
    source_alert_id: UUID | None = None
    incident_id: UUID | None = None
    action_key: str | None = None


@dataclass(frozen=True)
class TaskRecord:
    id: UUID
    origin: str
    kind: str
    status: str
    title: str
    action_key: str | None
    source_alert_id: UUID | None
    due_at: datetime


class EngagementRepository(Protocol):
    async def upsert_system_templates(self, templates: Sequence[Template]) -> None: ...

    async def templates(self) -> list[Template]: ...

    async def template_states(self) -> dict[UUID, TemplateState]: ...

    async def templates_with_task(self, day: date | None) -> set[UUID]: ...

    async def insert_task(self, task: NewTask) -> bool: ...

    async def task(self, task_id: UUID, *, lock: bool = False) -> TaskRecord | None: ...

    async def update_task(
        self, task_id: UUID, *, title: str, zone_id: UUID | None, due_at: datetime
    ) -> None: ...

    async def delete_task(self, task_id: UUID) -> None: ...

    async def complete(self, task_id: UUID, effective: bool | None, at: datetime) -> None: ...

    async def block(self, task_id: UUID, reason: str) -> None: ...

    async def snooze(self, task_id: UUID, minutes: int) -> None: ...

    async def open_incident_task(self, incident_id: UUID) -> TaskRecord | None: ...

    async def last_applied_plan(self) -> int | None: ...

    async def apply_actions(self, actions: Sequence[PlanAction], plan_version: int) -> None: ...

    async def record_plan(
        self,
        plan_version: int,
        batch_id: UUID,
        applied: Sequence[UUID],
        rejected: Sequence[dict[str, Any]],
        at: datetime,
    ) -> None: ...
