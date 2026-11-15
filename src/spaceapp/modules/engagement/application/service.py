"""Casos de uso de Misiones y tareas: tareas del día, tareas propias, incidentes y planes de Tierra.

Cada cambio y su evento se escriben en la misma transacción.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.engagement.contracts import (
    GroundPlanApplied,
    RejectedItem,
    TaskAssigned,
    TaskBlocked,
    TaskCompleted,
    TaskCreated,
)
from spaceapp.modules.engagement.domain.plans import PlanItem, plan_actions
from spaceapp.modules.engagement.domain.tasks import (
    Template,
    can_change,
    check_block,
    check_new_task,
    due_instances,
)
from spaceapp.modules.engagement.ports import EngagementRepository, NewTask, TaskRecord
from spaceapp.modules.facility.contracts import IncidentOpened, IncidentResolved
from spaceapp.modules.groundlink.contracts import GroundPlanReceived
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.outbox import UnitOfWork

CONSUMERS = {
    "facility.incident_opened": "engagement.on_incident_opened",
    "facility.incident_resolved": "engagement.on_incident_resolved",
    "knowledge.recommendation_ready": "engagement.on_recommendation_ready",
    "groundlink.ground_plan_received": "engagement.on_ground_plan_received",
}

Publish = Callable[[EventEnvelope], Awaitable[None]]
RepositoryFactory = Callable[[AsyncSession], EngagementRepository]


@dataclass(frozen=True)
class Done:
    task_id: UUID
    already: bool = False


@dataclass(frozen=True)
class Failed:
    code: str
    message: str


Outcome = Done | Failed

_MESSAGES = {
    "INVALID_KIND": "la tripulación crea tareas de SALUD o NAVE; las de incidente son del sistema",
    "TITLE_REQUIRED": "la tarea necesita un título",
    "REASON_REQUIRED": "para bloquear una tarea hay que dar el motivo",
    "ALREADY_COMPLETED": "la tarea ya está completada",
}


def _failed(code: str) -> Failed:
    return Failed(code, _MESSAGES[code])


class EngagementService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: RepositoryFactory,
        *,
        system_templates: Sequence[Template],
        zone_codes: set[str],
        zone_id_of: Callable[[str], UUID],
        crew_member: UUID,
        habitat_id: UUID,
        action_title: Callable[[str], str | None],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sf = session_factory
        self._repo = repository
        self._system = list(system_templates)
        self.zone_codes = zone_codes
        self._zone_id_of = zone_id_of
        self.crew_member = crew_member
        self._habitat = habitat_id
        self._action_title = action_title
        self._clock = clock
        self._seeded = False

    def today(self) -> date:
        return self._clock().astimezone(UTC).date()

    # --- Tareas del día ------------------------------------------------------------------

    async def ensure_day(self, day: date | None = None) -> None:
        """Crea, una sola vez, la tarea del día de cada plantilla activa."""
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            if not self._seeded:
                await repo.upsert_system_templates(self._system)
                self._seeded = True
            await self._materialize(repo, uow.publish, day or self.today())

    async def _materialize(
        self,
        repo: EngagementRepository,
        publish: Publish,
        day: date,
        cause: EventEnvelope | None = None,
    ) -> None:
        templates = await repo.templates()
        due = due_instances(
            templates,
            day,
            today=await repo.templates_with_task(day),
            ever=await repo.templates_with_task(None),
        )
        for t in due:
            hour, minute = (int(x) for x in t.due_time.split(":"))
            await self._create(
                repo,
                publish,
                NewTask(
                    id=uuid4(),
                    crew_member_id=self.crew_member,
                    template_id=t.id,
                    origin=t.origin,
                    kind=t.kind,
                    title=t.title,
                    zone_id=self._zone_id_of(t.zone_code) if t.zone_code else None,
                    day=day,
                    due_at=datetime.combine(day, time(hour, minute), UTC),
                ),
                cause=cause,
            )

    async def _create(
        self,
        repo: EngagementRepository,
        publish: Publish,
        task: NewTask,
        *,
        cause: EventEnvelope | None = None,
    ) -> bool:
        if not await repo.insert_task(task):
            return False  # ya existía (idempotencia por plantilla y día, incidente o alerta)
        await publish(
            self._event(
                TaskAssigned(
                    task_id=task.id,
                    crew_member_id=task.crew_member_id,
                    kind=task.kind,
                    origin=task.origin,
                    action_key=task.action_key,
                    due_at=task.due_at,
                ),
                task.id,
                cause,
            )
        )
        return True

    # --- Handlers del bus ----------------------------------------------------------------

    async def on_incident_opened(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        incident = event.payload_as(IncidentOpened)
        now = event.occurred_at
        await self._create(
            self._repo(_session(ctx)),
            ctx.publish,
            NewTask(
                id=uuid4(),
                crew_member_id=self.crew_member,
                template_id=None,
                origin="SISTEMA",
                kind="INCIDENTE",
                title=f"Atender: {incident.title}",
                zone_id=incident.zone_id,
                day=now.astimezone(UTC).date(),
                due_at=now,
                incident_id=incident.incident_id,
            ),
            cause=event,
        )

    async def on_incident_resolved(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        resolved = event.payload_as(IncidentResolved)
        repo = self._repo(_session(ctx))
        task = await repo.open_incident_task(resolved.incident_id)
        if task is None:
            return
        await repo.complete(task.id, None, resolved.resolved_at)
        await ctx.publish(
            self._event(
                TaskCompleted(task_id=task.id, action_key=None, effective=None), task.id, event
            )
        )

    async def on_recommendation_ready(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """Cada acción recomendada para una alerta es una medida del día (no suma a la racha)."""
        recommendation = event.payload_as(RecommendationReady)
        repo = self._repo(_session(ctx))
        now = event.occurred_at
        for key in recommendation.action_keys:
            await self._create(
                repo,
                ctx.publish,
                NewTask(
                    id=uuid4(),
                    crew_member_id=self.crew_member,
                    template_id=None,
                    origin="SISTEMA",
                    kind="SALUD",
                    title=self._action_title(key) or key,
                    zone_id=None,
                    day=now.astimezone(UTC).date(),
                    due_at=now,
                    source_alert_id=recommendation.alert_id,
                    action_key=key,
                ),
                cause=event,
            )

    async def on_ground_plan_received(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """Aplica el plan en una transacción. Lo completado o creado a bordo no se toca."""
        plan = event.payload_as(GroundPlanReceived)
        repo = self._repo(_session(ctx))
        last = await repo.last_applied_plan()
        if last is not None and plan.plan_version <= last:
            return  # versión menor o repetida: se ignora
        items = [
            PlanItem(c.change, c.kind, c.title, c.recurrence, c.zone_code, c.target_template_id)
            for c in plan.changes
        ]
        actions, rejected = plan_actions(items, await repo.template_states(), self.zone_codes)
        await repo.apply_actions(actions, plan.plan_version)
        applied = [a.template_id for a in actions]
        reasons = [{"title": r.title, "reason": r.reason} for r in rejected]
        await repo.record_plan(
            plan.plan_version, plan.batch_id, applied, reasons, event.occurred_at
        )
        await ctx.publish(
            self._event(
                GroundPlanApplied(
                    plan_version=plan.plan_version,
                    applied=applied,
                    rejected=[RejectedItem(title=r.title, reason=r.reason) for r in rejected],
                ),
                plan.batch_id,
                event,
                aggregate_type="ground_plan",
            )
        )
        # Las plantillas nuevas ya tienen su tarea de hoy; los cambios rigen para las siguientes.
        await self._materialize(repo, ctx.publish, self.today(), cause=event)

    # --- Mutaciones de la tripulación ----------------------------------------------------

    async def create(
        self, kind: str, title: str, zone_id: UUID | None, due_at: datetime | None
    ) -> Outcome:
        error = check_new_task(kind, title)
        if error:
            return _failed(error)
        due = due_at or self._clock()
        task_id = uuid4()
        async with UnitOfWork(self._sf) as uow:
            await self._repo(uow.session).insert_task(
                NewTask(
                    id=task_id,
                    crew_member_id=self.crew_member,
                    template_id=None,
                    origin="TRIPULACION",
                    kind=kind,
                    title=title.strip(),
                    zone_id=zone_id,
                    day=due.astimezone(UTC).date(),
                    due_at=due,
                )
            )
            await uow.publish(
                self._event(
                    TaskCreated(
                        task_id=task_id,
                        kind=kind,
                        title=title.strip(),
                        zone_id=zone_id,
                        origin="TRIPULACION",
                    ),
                    task_id,
                )
            )
        return Done(task_id)

    async def update(
        self, task_id: UUID, *, title: str | None, zone_id: UUID | None, due_at: datetime | None
    ) -> Outcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if not can_change(task.origin):
                return Failed("NOT_EDITABLE", f"una tarea de {task.origin} no se edita")
            if title is not None and not title.strip():
                return _failed("TITLE_REQUIRED")
            await repo.update_task(
                task_id,
                title=title.strip() if title else task.title,
                zone_id=zone_id,
                due_at=due_at or task.due_at,
            )
        return Done(task_id)

    async def delete(self, task_id: UUID) -> Outcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if not can_change(task.origin):
                return Failed(
                    "NOT_DELETABLE", f"una tarea de {task.origin} no se borra: se puede bloquear"
                )
            await repo.delete_task(task_id)
        return Done(task_id)

    async def complete(self, task_id: UUID, effective: bool | None) -> Outcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if task.status == "COMPLETADA":
                return Done(task_id, already=True)
            await repo.complete(task_id, effective, self._clock())
            await uow.publish(
                self._event(
                    TaskCompleted(task_id=task_id, action_key=task.action_key, effective=effective),
                    task_id,
                )
            )
        return Done(task_id)

    async def block(self, task_id: UUID, reason: str) -> Outcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            error = check_block(task.status, reason)
            if error:
                return _failed(error)
            await repo.block(task_id, reason.strip())
            await uow.publish(
                self._event(
                    TaskBlocked(task_id=task_id, origin=task.origin, reason=reason.strip()),
                    task_id,
                )
            )
        return Done(task_id)

    async def snooze(self, task_id: UUID, minutes: int) -> Outcome:
        if not 1 <= minutes <= 24 * 60:
            return Failed("INVALID_MINUTES", "se pospone entre 1 minuto y 24 horas")
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if task.status == "COMPLETADA":
                return _failed("ALREADY_COMPLETED")
            await repo.snooze(task_id, minutes)
        return Done(task_id)

    # --- Apoyo ---------------------------------------------------------------------------

    def _event(
        self,
        payload: EventPayload,
        aggregate_id: UUID,
        cause: EventEnvelope | None = None,
        *,
        aggregate_type: str = "task",
    ) -> EventEnvelope:
        return EventEnvelope.from_payload(
            payload,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            partition_key=f"habitat:{self._habitat}",
            correlation_id=(cause.correlation_id or cause.event_id) if cause else None,
            causation_id=cause.event_id if cause else None,
        )


def _not_found(task_id: UUID) -> Failed:
    return Failed("NOT_FOUND", f"no existe la tarea {task_id}")


def _session(ctx: HandlerContext) -> AsyncSession:
    if ctx.session is None:
        raise RuntimeError("Misiones necesita la sesión del relay del outbox")
    return ctx.session


__all__ = ["CONSUMERS", "Done", "EngagementService", "Failed", "Outcome", "TaskRecord"]
