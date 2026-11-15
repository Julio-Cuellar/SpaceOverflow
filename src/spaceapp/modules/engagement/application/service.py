"""Missions and tasks use cases: daily tasks, own tasks, incidents and Ground plans.

Every change and its event are written in the same transaction.
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
    "INVALID_KIND": "the crew creates HEALTH or SHIP tasks; incident tasks belong to the system",
    "TITLE_REQUIRED": "the task needs a title",
    "REASON_REQUIRED": "a reason is required to block a task",
    "ALREADY_COMPLETED": "the task is already completed",
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

    # --- Daily tasks ------------------------------------------------------------------

    async def ensure_day(self, day: date | None = None) -> None:
        """Creates, once, the daily task of each active template."""
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
            return False  # already existed (idempotent per template and day, incident or alert)
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

    # --- Bus handlers ----------------------------------------------------------------

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
                origin="SYSTEM",
                kind="INCIDENT",
                title=f"Attend to: {incident.title}",
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
        """Each action recommended for an alert is a task of the day (no streak credit)."""
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
                    origin="SYSTEM",
                    kind="HEALTH",
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
        """Applies the plan in one transaction. Whatever was completed or created on board stays."""
        plan = event.payload_as(GroundPlanReceived)
        repo = self._repo(_session(ctx))
        last = await repo.last_applied_plan()
        if last is not None and plan.plan_version <= last:
            return  # older or repeated version: ignored
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
        # New templates already get today's task; changes apply to the following ones.
        await self._materialize(repo, ctx.publish, self.today(), cause=event)

    # --- Crew mutations ----------------------------------------------------

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
                    origin="CREW",
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
                        origin="CREW",
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
                return Failed("NOT_EDITABLE", f"a {task.origin} task cannot be edited")
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
                    "NOT_DELETABLE", f"a {task.origin} task cannot be deleted: it can be blocked"
                )
            await repo.delete_task(task_id)
        return Done(task_id)

    async def complete(self, task_id: UUID, effective: bool | None) -> Outcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if task.status == "COMPLETED":
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
            return Failed("INVALID_MINUTES", "snooze must be between 1 minute and 24 hours")
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            task = await repo.task(task_id, lock=True)
            if task is None:
                return _not_found(task_id)
            if task.status == "COMPLETED":
                return _failed("ALREADY_COMPLETED")
            await repo.snooze(task_id, minutes)
        return Done(task_id)

    # --- Support ---------------------------------------------------------------------------

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
    return Failed("NOT_FOUND", f"task {task_id} does not exist")


def _session(ctx: HandlerContext) -> AsyncSession:
    if ctx.session is None:
        raise RuntimeError("Missions needs the outbox relay session")
    return ctx.session


__all__ = ["CONSUMERS", "Done", "EngagementService", "Failed", "Outcome", "TaskRecord"]
