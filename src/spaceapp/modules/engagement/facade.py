"""Read-only queries of Missions and tasks (for the interface and the Ground Link)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class TaskView:
    id: UUID
    kind: str
    origin: str
    title: str
    zone_id: UUID | None
    status: str
    due_at: datetime
    blocked_reason: str | None
    effective: bool | None
    source_alert_id: UUID | None
    incident_id: UUID | None
    template_id: UUID | None
    completed_at: datetime | None


@dataclass(frozen=True)
class GroundTemplateStatus:
    """A Ground template as Ground sees it: active or cancelled, and its latest task."""

    template_id: UUID
    title: str
    kind: str
    active: bool
    plan_version: int | None
    task_status: str | None
    blocked_reason: str | None


_TASK = (
    "SELECT id, kind, origin, title, zone_id, status, due_at, blocked_reason, effective, "
    "source_alert_id, incident_id, template_id, completed_at FROM engagement.task"
)


class TaskQuery:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def day(
        self,
        day: date,
        *,
        crew_member_id: UUID | None = None,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[TaskView]:
        where = ["day = :d"]
        params: dict[str, Any] = {"d": day}
        for column, value in (
            ("crew_member_id", crew_member_id),
            ("kind", kind),
            ("status", status),
        ):
            if value is not None:
                where.append(f"{column} = :{column}")
                params[column] = value
        sql = f"{_TASK} WHERE {' AND '.join(where)} ORDER BY due_at, title, id"
        async with self._sf() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [TaskView(*r) for r in rows]

    async def get(self, task_id: UUID) -> TaskView | None:
        async with self._sf() as session:
            row = (await session.execute(text(_TASK + " WHERE id = :i"), {"i": task_id})).first()
        return TaskView(*row) if row else None

    async def last_applied_plan(self) -> dict[str, Any] | None:
        async with self._sf() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT plan_version, applied_at, rejected FROM engagement.applied_plan "
                        "ORDER BY plan_version DESC LIMIT 1"
                    )
                )
            ).first()
        if row is None:
            return None
        return {"plan_version": row[0], "applied_at": row[1], "rejected": row[2]}


class GroundTemplateQuery:
    """Status of the Ground templates. The Ground Link reads it for its panel."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def list(self) -> list[GroundTemplateStatus]:
        sql = (
            "SELECT t.id, t.title, t.kind, t.active, t.plan_version, k.status, k.blocked_reason "
            "FROM engagement.task_template t LEFT JOIN LATERAL ("
            "  SELECT status, blocked_reason FROM engagement.task WHERE template_id = t.id "
            "  ORDER BY day DESC, created_at DESC LIMIT 1"
            ") k ON true WHERE t.origin = 'GROUND' ORDER BY t.plan_version, t.title"
        )
        async with self._sf() as session:
            rows = (await session.execute(text(sql))).all()
        return [GroundTemplateStatus(*r) for r in rows]
