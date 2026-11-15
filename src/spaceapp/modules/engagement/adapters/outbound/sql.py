"""Missions and tasks repository on PostgreSQL. Works inside the received transaction."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.engagement.domain.plans import PlanAction, TemplateState
from spaceapp.modules.engagement.domain.tasks import Template
from spaceapp.modules.engagement.ports import NewTask, TaskRecord

_TEMPLATE = "SELECT id, kind, title, recurrence, zone_code, origin, active, due_time FROM engagement.task_template"
_TASK = (
    "SELECT id, origin, kind, status, title, action_key, source_alert_id, due_at "
    "FROM engagement.task"
)


class SqlEngagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_system_templates(self, templates: Sequence[Template]) -> None:
        for t in templates:
            await self._s.execute(
                text(
                    "INSERT INTO engagement.task_template (id, kind, title, recurrence, zone_code, "
                    "origin, active, due_time) VALUES (:id, :k, :t, :r, :z, 'SYSTEM', :a, :d) "
                    "ON CONFLICT (id) DO UPDATE SET kind = EXCLUDED.kind, title = EXCLUDED.title, "
                    "recurrence = EXCLUDED.recurrence, zone_code = EXCLUDED.zone_code, "
                    "active = EXCLUDED.active, due_time = EXCLUDED.due_time, updated_at = now()"
                ),
                {
                    "id": t.id,
                    "k": t.kind,
                    "t": t.title,
                    "r": t.recurrence,
                    "z": t.zone_code,
                    "a": t.active,
                    "d": t.due_time,
                },
            )

    async def templates(self) -> list[Template]:
        rows = await self._s.execute(text(_TEMPLATE + " ORDER BY due_time, id"))
        return [Template(*r) for r in rows]

    async def template_states(self) -> dict[UUID, TemplateState]:
        rows = await self._s.execute(
            text("SELECT id, origin, active FROM engagement.task_template")
        )
        return {r[0]: TemplateState(r[0], r[1], r[2]) for r in rows}

    async def templates_with_task(self, day: date | None) -> set[UUID]:
        sql = "SELECT DISTINCT template_id FROM engagement.task WHERE template_id IS NOT NULL"
        params: dict[str, Any] = {}
        if day is not None:
            sql += " AND day = :d"
            params["d"] = day
        return {r[0] for r in await self._s.execute(text(sql), params)}

    async def insert_task(self, task: NewTask) -> bool:
        inserted = (
            await self._s.execute(
                text(
                    "INSERT INTO engagement.task (id, crew_member_id, template_id, origin, kind, "
                    "title, zone_id, day, due_at, source_alert_id, incident_id, action_key) VALUES "
                    "(:id, :c, :tpl, :o, :k, :t, :z, :day, :due, :a, :i, :ak) "
                    "ON CONFLICT DO NOTHING RETURNING id"
                ),
                {
                    "id": task.id,
                    "c": task.crew_member_id,
                    "tpl": task.template_id,
                    "o": task.origin,
                    "k": task.kind,
                    "t": task.title,
                    "z": task.zone_id,
                    "day": task.day,
                    "due": task.due_at,
                    "a": task.source_alert_id,
                    "i": task.incident_id,
                    "ak": task.action_key,
                },
            )
        ).first()
        return inserted is not None

    async def task(self, task_id: UUID, *, lock: bool = False) -> TaskRecord | None:
        sql = _TASK + " WHERE id = :i" + (" FOR UPDATE" if lock else "")
        row = (await self._s.execute(text(sql), {"i": task_id})).first()
        return TaskRecord(*row) if row else None

    async def update_task(
        self, task_id: UUID, *, title: str, zone_id: UUID | None, due_at: datetime
    ) -> None:
        await self._s.execute(
            text(
                "UPDATE engagement.task SET title = :t, zone_id = :z, due_at = :d, "
                "day = (CAST(:d AS timestamptz) AT TIME ZONE 'UTC')::date WHERE id = :i"
            ),
            {"t": title, "z": zone_id, "d": due_at, "i": task_id},
        )

    async def delete_task(self, task_id: UUID) -> None:
        await self._s.execute(text("DELETE FROM engagement.task WHERE id = :i"), {"i": task_id})

    async def complete(self, task_id: UUID, effective: bool | None, at: datetime) -> None:
        await self._s.execute(
            text(
                "UPDATE engagement.task SET status = 'COMPLETED', effective = :e, "
                "completed_at = :t WHERE id = :i"
            ),
            {"e": effective, "t": at, "i": task_id},
        )

    async def block(self, task_id: UUID, reason: str) -> None:
        await self._s.execute(
            text(
                "UPDATE engagement.task SET status = 'BLOCKED', blocked_reason = :r WHERE id = :i"
            ),
            {"r": reason, "i": task_id},
        )

    async def snooze(self, task_id: UUID, minutes: int) -> None:
        await self._s.execute(
            text(
                "UPDATE engagement.task SET due_at = due_at + make_interval(mins => :m) "
                "WHERE id = :i"
            ),
            {"m": minutes, "i": task_id},
        )

    async def open_incident_task(self, incident_id: UUID) -> TaskRecord | None:
        row = (
            await self._s.execute(
                text(_TASK + " WHERE incident_id = :i AND status <> 'COMPLETED' FOR UPDATE"),
                {"i": incident_id},
            )
        ).first()
        return TaskRecord(*row) if row else None

    async def last_applied_plan(self) -> int | None:
        value = (
            await self._s.execute(text("SELECT max(plan_version) FROM engagement.applied_plan"))
        ).scalar_one()
        return int(value) if value is not None else None

    async def apply_actions(self, actions: Sequence[PlanAction], plan_version: int) -> None:
        for a in actions:
            if a.change == "NEW":
                await self._s.execute(
                    text(
                        "INSERT INTO engagement.task_template (id, kind, title, recurrence, "
                        "zone_code, origin, plan_version) VALUES (:id, :k, :t, :r, :z, 'GROUND', :v)"
                    ),
                    {
                        "id": a.template_id,
                        "k": a.kind,
                        "t": a.title,
                        "r": a.recurrence,
                        "z": a.zone_code,
                        "v": plan_version,
                    },
                )
            elif a.change == "UPDATE":
                await self._s.execute(
                    text(
                        "UPDATE engagement.task_template SET kind = COALESCE(:k, kind), "
                        "title = COALESCE(:t, title), recurrence = COALESCE(:r, recurrence), "
                        "zone_code = COALESCE(:z, zone_code), plan_version = :v, active = true, "
                        "updated_at = now() WHERE id = :id"
                    ),
                    {
                        "id": a.template_id,
                        "k": a.kind,
                        "t": a.title,
                        "r": a.recurrence,
                        "z": a.zone_code,
                        "v": plan_version,
                    },
                )
            else:  # CANCEL: applies going forward; what was already created or completed is kept
                await self._s.execute(
                    text(
                        "UPDATE engagement.task_template SET active = false, plan_version = :v, "
                        "updated_at = now() WHERE id = :id"
                    ),
                    {"id": a.template_id, "v": plan_version},
                )

    async def record_plan(
        self,
        plan_version: int,
        batch_id: UUID,
        applied: Sequence[UUID],
        rejected: Sequence[dict[str, Any]],
        at: datetime,
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO engagement.applied_plan (plan_version, batch_id, applied, rejected, "
                "applied_at) VALUES (:v, :b, CAST(:a AS jsonb), CAST(:r AS jsonb), :t)"
            ),
            {
                "v": plan_version,
                "b": batch_id,
                "a": json.dumps([str(x) for x in applied]),
                "r": json.dumps(list(rejected), ensure_ascii=False),
                "t": at,
            },
        )
