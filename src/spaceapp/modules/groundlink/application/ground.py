"""Lado de Tierra (demo): borrador del plan, publicación y enlace simulado con demora y corte.

El plan viaja por el enlace hasta la nave (`PlanReceiver`). Si el enlace está cortado queda en
cola y se entrega al volver. La confirmación de la nave sube por el mismo enlace.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.groundlink.application.receiver import PlanReceiver
from spaceapp.modules.groundlink.contracts import BatchAcknowledged, LinkStateChanged
from spaceapp.modules.groundlink.domain.plans import (
    ShipTemplate,
    ShownTemplate,
    draft_templates,
    in_flight,
    plan_hash,
)
from spaceapp.modules.groundlink.ports import (
    GroundlinkRepository,
    GroundPlanRow,
    LinkState,
    Schedule,
    ShipTemplates,
)
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import UnitOfWork

CONSUMER_ACK = "groundlink.ground.on_batch_acknowledged"

RepositoryFactory = Callable[[AsyncSession], GroundlinkRepository]


@dataclass(frozen=True)
class GroundView:
    applied_version: int
    templates: list[ShownTemplate]
    draft_version: int | None
    draft: list[ShownTemplate] | None
    published: GroundPlanRow | None
    link: LinkState


@dataclass(frozen=True)
class Ok:
    plan_version: int | None = None


@dataclass(frozen=True)
class Refused:
    code: str  # NOT_FOUND, TITLE_REQUIRED, INVALID_KIND, NOTHING_TO_PUBLISH, PLAN_IN_FLIGHT
    message: str


GroundOutcome = Ok | Refused


class GroundControl:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: RepositoryFactory,
        receiver: PlanReceiver,
        ship_templates: ShipTemplates,
        schedule: Schedule,
        habitat_id: UUID,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sf = session_factory
        self._repo = repository
        self._receiver = receiver
        self._ship_templates = ship_templates
        self._schedule = schedule
        self._habitat = habitat_id
        self._clock = clock

    # --- Lectura -------------------------------------------------------------------------

    async def view(self) -> GroundView:
        active = await self._ship_templates()
        async with self._sf() as session:
            repo = self._repo(session)
            link = await repo.link()
            draft = await repo.draft()
            items = await repo.items(draft.id) if draft else []
            published = [p for p in await repo.plans() if p.status != "BORRADOR"]
            await session.commit()  # `link()` puede crear la fila del enlace
        applied = [p.version for p in published if p.status in ("APLICADO", "CONFIRMADO")]
        return GroundView(
            applied_version=max(applied, default=0),
            templates=draft_templates(active, []),
            draft_version=draft.version if draft else None,
            draft=draft_templates(active, items) if draft else None,
            published=published[-1] if published else None,
            link=link,
        )

    # --- Borrador ------------------------------------------------------------------------

    async def save_template(
        self,
        *,
        title: str,
        kind: str,
        zone_code: str | None = None,
        recurrence: str | None = None,
        template_id: UUID | None = None,
    ) -> GroundOutcome:
        if not title.strip():
            return Refused("TITLE_REQUIRED", "la plantilla necesita un título")
        if kind not in ("SALUD", "NAVE"):
            return Refused("INVALID_KIND", "Tierra programa tareas de SALUD o NAVE")
        active = {t.id for t in await self._ship_templates()}
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            draft = await self._draft(repo)
            in_draft = {i.template_id: i for i in await repo.items(draft.id)}
            if template_id is not None and template_id in active:
                change = "UPDATE"
            elif template_id is not None and template_id in in_draft:
                change = in_draft[template_id].change
            elif template_id is None:
                change, template_id = "NEW", uuid4()
            else:
                return Refused("NOT_FOUND", f"no existe la plantilla {template_id}")
            await repo.upsert_item(
                draft.id,
                change=change,
                template_id=template_id,
                kind=kind,
                title=title.strip(),
                recurrence=recurrence,
                zone_code=zone_code,
            )
        return Ok(draft.version)

    async def cancel_template(self, template_id: UUID) -> GroundOutcome:
        active = {t.id for t in await self._ship_templates()}
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            draft = await self._draft(repo)
            in_draft = {i.template_id: i for i in await repo.items(draft.id)}
            if template_id in in_draft and in_draft[template_id].change == "NEW":
                await repo.delete_item(draft.id, template_id)  # solo existía en el borrador
            elif template_id in active:
                await repo.upsert_item(
                    draft.id,
                    change="CANCEL",
                    template_id=template_id,
                    kind=None,
                    title=None,
                    recurrence=None,
                    zone_code=None,
                )
            else:
                return Refused("NOT_FOUND", f"no existe la plantilla {template_id}")
        return Ok(draft.version)

    async def _draft(self, repo: GroundlinkRepository) -> GroundPlanRow:
        draft = await repo.draft()
        if draft is None:
            await repo.create_draft(uuid4(), await repo.max_version() + 1)
            draft = await repo.draft()
        assert draft is not None
        return draft

    # --- Publicación y enlace ------------------------------------------------------------

    async def publish(self) -> GroundOutcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            if any(in_flight(p.status) for p in await repo.plans()):
                return Refused("PLAN_IN_FLIGHT", "hay un plan publicado sin confirmar")
            draft = await repo.draft()
            if draft is None or not await repo.items(draft.id):
                return Refused("NOTHING_TO_PUBLISH", "el borrador no tiene cambios")
            link = await repo.link()
            stage = "EN_EL_ENLACE" if link.online else "EN_COLA"
            await repo.set_status(draft.id, stage, batch_id=uuid4(), at=self._clock())
        if link.online:
            self._send(draft.id, link.delay_s)
        return Ok(draft.version)

    async def set_link(self, online: bool, delay_s: float | None = None) -> LinkState:
        now = self._clock()
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            current = await repo.link()
            delay = current.delay_s if delay_s is None else max(0.0, delay_s)
            await repo.set_link(online, delay, now)
            queued = await repo.plans(["EN_COLA"])
            if online:
                for plan in queued:
                    await repo.set_status(plan.id, "EN_EL_ENLACE", only_from=["EN_COLA"])
                # Las confirmaciones retenidas suben al volver el enlace.
                for plan in await repo.plans(["APLICADO"]):
                    await repo.set_status(plan.id, "CONFIRMADO", only_from=["APLICADO"], at=now)
            if online != current.online:
                await uow.publish(
                    EventEnvelope.from_payload(
                        LinkStateChanged(
                            state="UP" if online else "DOWN",
                            since=now,
                            queued=0 if online else len(queued),
                        ),
                        aggregate_type="ground_link",
                        aggregate_id=self._habitat,
                        partition_key=f"habitat:{self._habitat}",
                    )
                )
        if online:
            for plan in queued:
                self._send(plan.id, delay)
        return LinkState(online, delay, now)

    def _send(self, plan_id: UUID, delay_s: float) -> None:
        async def deliver() -> None:
            await self.deliver(plan_id)

        self._schedule(delay_s, deliver)

    async def deliver(self, plan_id: UUID) -> None:
        """Llega a la nave lo que estaba en el enlace. Si el enlace se cortó, vuelve a la cola."""
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            plan = await repo.plan(plan_id)
            if plan is None or plan.status != "EN_EL_ENLACE" or plan.batch_id is None:
                return
            if not (await repo.link()).online:
                await repo.set_status(plan_id, "EN_COLA", only_from=["EN_EL_ENLACE"])
                return
            items = await repo.item_dicts(plan_id)
        received = await self._receiver.receive(
            plan.batch_id, plan.version, items, plan_hash(plan.version, items)
        )
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            if received.status == "received":
                await repo.set_status(plan_id, "RECIBIDO", only_from=["EN_EL_ENLACE"])
            else:
                reason = received.reason or "la nave ya tiene una versión igual o más nueva"
                await repo.set_status(
                    plan_id, "RECHAZADO", only_from=["EN_EL_ENLACE"], reason=reason
                )

    async def on_batch_acknowledged(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """La nave confirmó el lote. Si el enlace está cortado, la confirmación espera."""
        ack = event.payload_as(BatchAcknowledged)
        if ctx.session is None:
            raise RuntimeError("el Enlace con Tierra necesita la sesión del relay del outbox")
        repo = self._repo(ctx.session)
        plan = await repo.plan_by_batch(ack.batch_id)
        if plan is None:
            return
        if (await repo.link()).online:
            await repo.set_status(plan.id, "CONFIRMADO", at=ack.acked_at)
        else:
            await repo.set_status(plan.id, "APLICADO")


def ship_template(
    template_id: UUID,
    title: str,
    kind: str,
    task_status: str | None,
    blocked_reason: str | None,
) -> ShipTemplate:
    """Estado que ve Tierra a partir de la última tarea de la plantilla en la nave."""
    status = task_status if task_status in ("COMPLETADA", "BLOQUEADA") else "APLICADA"
    return ShipTemplate(template_id, title, kind, status, blocked_reason)
