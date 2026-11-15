"""Fragmento GraphQL de Misiones (tareas del día) y del panel de Tierra (planes y enlace)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

import strawberry

from spaceapp.interfaces.graphql.common import GqlInfo, uuid_or_none
from spaceapp.modules.engagement.application.service import Done, Outcome
from spaceapp.modules.engagement.domain.tasks import TaskFacts
from spaceapp.modules.engagement.domain.tasks import streak as streak_of
from spaceapp.modules.engagement.facade import TaskView
from spaceapp.modules.groundlink.application.ground import GroundOutcome, GroundView, Ok
from spaceapp.modules.groundlink.domain.plans import ShownTemplate


@strawberry.enum
class TaskKind(Enum):
    SALUD = "SALUD"
    NAVE = "NAVE"
    INCIDENTE = "INCIDENTE"


@strawberry.enum
class TaskOrigin(Enum):
    TIERRA = "TIERRA"
    SISTEMA = "SISTEMA"
    TRIPULACION = "TRIPULACION"


@strawberry.enum
class TaskStatus(Enum):
    PENDIENTE = "PENDIENTE"
    COMPLETADA = "COMPLETADA"
    BLOQUEADA = "BLOQUEADA"


@strawberry.enum
class TaskErrorCode(Enum):
    NOT_FOUND = "NOT_FOUND"
    NOT_EDITABLE = "NOT_EDITABLE"
    NOT_DELETABLE = "NOT_DELETABLE"
    INVALID_KIND = "INVALID_KIND"
    TITLE_REQUIRED = "TITLE_REQUIRED"
    REASON_REQUIRED = "REASON_REQUIRED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    INVALID_MINUTES = "INVALID_MINUTES"


@strawberry.enum
class PlanStage(Enum):
    BORRADOR = "BORRADOR"
    EN_COLA = "EN_COLA"
    EN_EL_ENLACE = "EN_EL_ENLACE"
    RECIBIDO = "RECIBIDO"
    APLICADO = "APLICADO"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"


@strawberry.enum
class GroundTemplateStatus(Enum):
    PENDIENTE = "PENDIENTE"
    APLICADA = "APLICADA"
    COMPLETADA = "COMPLETADA"
    BLOQUEADA = "BLOQUEADA"


@strawberry.enum
class GroundErrorCode(Enum):
    NOT_FOUND = "NOT_FOUND"
    TITLE_REQUIRED = "TITLE_REQUIRED"
    INVALID_KIND = "INVALID_KIND"
    NOTHING_TO_PUBLISH = "NOTHING_TO_PUBLISH"
    PLAN_IN_FLIGHT = "PLAN_IN_FLIGHT"


# --- Tareas --------------------------------------------------------------------------------


def _id(value: UUID | None) -> strawberry.ID | None:
    return strawberry.ID(str(value)) if value else None


@strawberry.type
class Task:
    id: strawberry.ID
    kind: TaskKind
    origin: TaskOrigin
    title: str
    zone_id: strawberry.ID | None
    status: TaskStatus
    due_at: datetime
    blocked_reason: str | None
    effective: bool | None
    source_alert_id: strawberry.ID | None
    incident_id: strawberry.ID | None
    template_id: strawberry.ID | None
    completed_at: datetime | None

    @staticmethod
    def of(t: TaskView) -> Task:
        return Task(
            id=strawberry.ID(str(t.id)),
            kind=TaskKind(t.kind),
            origin=TaskOrigin(t.origin),
            title=t.title,
            zone_id=_id(t.zone_id),
            status=TaskStatus(t.status),
            due_at=t.due_at,
            blocked_reason=t.blocked_reason,
            effective=t.effective,
            source_alert_id=_id(t.source_alert_id),
            incident_id=_id(t.incident_id),
            template_id=_id(t.template_id),
            completed_at=t.completed_at,
        )


@strawberry.type
class TaskPayload:
    task: Task
    already_done: bool


@strawberry.type
class TaskDeleted:
    id: strawberry.ID


@strawberry.type
class TaskError:
    code: TaskErrorCode
    message: str


TaskResult = Annotated[TaskPayload | TaskError, strawberry.union("TaskResult")]
DeleteTaskResult = Annotated[TaskDeleted | TaskError, strawberry.union("DeleteTaskResult")]


@strawberry.type
class RejectedPlanItem:
    title: str
    reason: str


@strawberry.type
class GroundPlanOnBoard:
    """El último plan de Tierra aplicado en la nave (lo que ve la tripulación)."""

    version: int
    applied_at: datetime
    rejected: list[RejectedPlanItem]


async def _task_result(info: GqlInfo, outcome: Outcome) -> TaskPayload | TaskError:
    if not isinstance(outcome, Done):
        return TaskError(code=TaskErrorCode(outcome.code), message=outcome.message)
    view = await info.context.services.tasks.get(outcome.task_id)
    assert view is not None  # se acaba de escribir en la misma base
    return TaskPayload(task=Task.of(view), already_done=outcome.already)


def _missing(value: str) -> TaskError:
    return TaskError(code=TaskErrorCode.NOT_FOUND, message=f"no existe la tarea {value}")


# --- Panel de Tierra -----------------------------------------------------------------------


@strawberry.type
class GroundTemplate:
    id: strawberry.ID
    title: str
    kind: TaskKind
    status: GroundTemplateStatus
    blocked_reason: str | None
    cancelled: bool

    @staticmethod
    def of(t: ShownTemplate) -> GroundTemplate:
        return GroundTemplate(
            id=strawberry.ID(str(t.id)),
            title=t.title,
            kind=TaskKind(t.kind),
            status=GroundTemplateStatus(t.status),
            blocked_reason=t.blocked_reason,
            cancelled=t.cancelled,
        )


@strawberry.type
class GroundDraft:
    version: int
    templates: list[GroundTemplate]


@strawberry.type
class PublishedPlan:
    version: int
    stage: PlanStage
    reason: str | None
    published_at: datetime | None
    acked_at: datetime | None


@strawberry.type
class GroundLinkState:
    online: bool
    delay_seconds: float
    changed_at: datetime


@strawberry.type
class GroundControlView:
    applied_version: int
    templates: list[GroundTemplate]
    draft: GroundDraft | None
    published: PublishedPlan | None
    link: GroundLinkState

    @staticmethod
    def of(v: GroundView) -> GroundControlView:
        p = v.published
        return GroundControlView(
            applied_version=v.applied_version,
            templates=[GroundTemplate.of(t) for t in v.templates],
            draft=(
                GroundDraft(
                    version=v.draft_version, templates=[GroundTemplate.of(t) for t in v.draft]
                )
                if v.draft is not None and v.draft_version is not None
                else None
            ),
            published=(
                PublishedPlan(
                    version=p.version,
                    stage=PlanStage(p.status),
                    reason=p.reason,
                    published_at=p.published_at,
                    acked_at=p.acked_at,
                )
                if p
                else None
            ),
            link=GroundLinkState(
                online=v.link.online, delay_seconds=v.link.delay_s, changed_at=v.link.changed_at
            ),
        )


@strawberry.type
class GroundError:
    code: GroundErrorCode
    message: str


GroundResult = Annotated[GroundControlView | GroundError, strawberry.union("GroundResult")]


async def _ground_result(info: GqlInfo, outcome: GroundOutcome) -> GroundControlView | GroundError:
    if not isinstance(outcome, Ok):
        return GroundError(code=GroundErrorCode(outcome.code), message=outcome.message)
    return GroundControlView.of(await info.context.services.ground.view())


# --- Raíces --------------------------------------------------------------------------------


@strawberry.type
class MissionsQuery:
    @strawberry.field
    async def tasks(
        self,
        info: GqlInfo,
        day: date | None = None,
        kind: TaskKind | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        services = info.context.services
        wanted = day or services.engagement.today()
        await services.engagement.ensure_day(wanted)
        views = await services.tasks.day(
            wanted,
            crew_member_id=services.crew_member,
            kind=kind.value if kind else None,
            status=status.value if status else None,
        )
        return [Task.of(t) for t in views]

    @strawberry.field
    async def streak(self, info: GqlInfo, day: date | None = None) -> int:
        """Rutinas de salud completadas en el día. Ni Tierra, ni incidentes, ni alertas suman."""
        services = info.context.services
        views = await services.tasks.day(
            day or services.engagement.today(), crew_member_id=services.crew_member
        )
        return streak_of(TaskFacts(t.kind, t.origin, t.status, t.source_alert_id) for t in views)

    @strawberry.field
    async def ground_plan(self, info: GqlInfo) -> GroundPlanOnBoard | None:
        last = await info.context.services.tasks.last_applied_plan()
        if last is None:
            return None
        rejected = last["rejected"] or []
        return GroundPlanOnBoard(
            version=last["plan_version"],
            applied_at=last["applied_at"],
            rejected=[RejectedPlanItem(title=r["title"], reason=r["reason"]) for r in rejected],
        )

    @strawberry.field
    async def ground_control(self, info: GqlInfo) -> GroundControlView:
        """Panel del centro de control (rol `ground`, sin autenticación en la demo)."""
        return GroundControlView.of(await info.context.services.ground.view())


@strawberry.type
class MissionsMutation:
    @strawberry.mutation
    async def create_task(
        self,
        info: GqlInfo,
        kind: TaskKind,
        title: str,
        zone_id: strawberry.ID | None = None,
        due_at: datetime | None = None,
    ) -> TaskResult:
        zone = uuid_or_none(zone_id) if zone_id else None
        outcome = await info.context.services.engagement.create(kind.value, title, zone, due_at)
        return await _task_result(info, outcome)

    @strawberry.mutation
    async def update_task(
        self,
        info: GqlInfo,
        id: strawberry.ID,
        title: str | None = None,
        zone_id: strawberry.ID | None = None,
        due_at: datetime | None = None,
    ) -> TaskResult:
        task_id = uuid_or_none(id)
        if task_id is None:
            return _missing(id)
        zone = uuid_or_none(zone_id) if zone_id else None
        outcome = await info.context.services.engagement.update(
            task_id, title=title, zone_id=zone, due_at=due_at
        )
        return await _task_result(info, outcome)

    @strawberry.mutation
    async def delete_task(self, info: GqlInfo, id: strawberry.ID) -> DeleteTaskResult:
        task_id = uuid_or_none(id)
        if task_id is None:
            return _missing(id)
        outcome = await info.context.services.engagement.delete(task_id)
        if isinstance(outcome, Done):
            return TaskDeleted(id=id)
        return TaskError(code=TaskErrorCode(outcome.code), message=outcome.message)

    @strawberry.mutation
    async def complete_task(
        self, info: GqlInfo, id: strawberry.ID, effective: bool | None = None
    ) -> TaskResult:
        task_id = uuid_or_none(id)
        if task_id is None:
            return _missing(id)
        return await _task_result(
            info, await info.context.services.engagement.complete(task_id, effective)
        )

    @strawberry.mutation
    async def block_task(self, info: GqlInfo, id: strawberry.ID, reason: str) -> TaskResult:
        task_id = uuid_or_none(id)
        if task_id is None:
            return _missing(id)
        return await _task_result(
            info, await info.context.services.engagement.block(task_id, reason)
        )

    @strawberry.mutation
    async def snooze_task(self, info: GqlInfo, id: strawberry.ID, minutes: int = 15) -> TaskResult:
        task_id = uuid_or_none(id)
        if task_id is None:
            return _missing(id)
        return await _task_result(
            info, await info.context.services.engagement.snooze(task_id, minutes)
        )

    @strawberry.mutation
    async def save_ground_template(
        self,
        info: GqlInfo,
        title: str,
        kind: TaskKind,
        zone_code: str | None = None,
        recurrence: str | None = None,
        template_id: strawberry.ID | None = None,
    ) -> GroundResult:
        target = uuid_or_none(template_id) if template_id else None
        if template_id and target is None:
            return GroundError(code=GroundErrorCode.NOT_FOUND, message=f"no existe {template_id}")
        outcome = await info.context.services.ground.save_template(
            title=title,
            kind=kind.value,
            zone_code=zone_code,
            recurrence=recurrence,
            template_id=target,
        )
        return await _ground_result(info, outcome)

    @strawberry.mutation
    async def cancel_ground_template(
        self, info: GqlInfo, template_id: strawberry.ID
    ) -> GroundResult:
        target = uuid_or_none(template_id)
        if target is None:
            return GroundError(code=GroundErrorCode.NOT_FOUND, message=f"no existe {template_id}")
        return await _ground_result(
            info, await info.context.services.ground.cancel_template(target)
        )

    @strawberry.mutation
    async def publish_ground_plan(self, info: GqlInfo) -> GroundResult:
        return await _ground_result(info, await info.context.services.ground.publish())

    @strawberry.mutation
    async def set_ground_link(
        self, info: GqlInfo, online: bool, delay_seconds: float | None = None
    ) -> GroundControlView:
        ground = info.context.services.ground
        await ground.set_link(online, delay_seconds)
        return GroundControlView.of(await ground.view())
