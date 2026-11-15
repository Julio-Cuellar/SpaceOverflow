"""Ground side (demo): plan draft, publishing and a simulated link with delay and outages.

The plan travels over the link to the ship (`PlanReceiver`). If the link is down it stays
queued and is delivered when the link returns. The ship's acknowledgement goes back over the
same link.
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

    # --- Reading -------------------------------------------------------------------------

    async def view(self) -> GroundView:
        active = await self._ship_templates()
        async with self._sf() as session:
            repo = self._repo(session)
            link = await repo.link()
            draft = await repo.draft()
            items = await repo.items(draft.id) if draft else []
            published = [p for p in await repo.plans() if p.status != "DRAFT"]
            await session.commit()  # `link()` may create the link row
        applied = [p.version for p in published if p.status in ("APPLIED", "CONFIRMED")]
        return GroundView(
            applied_version=max(applied, default=0),
            templates=draft_templates(active, []),
            draft_version=draft.version if draft else None,
            draft=draft_templates(active, items) if draft else None,
            published=published[-1] if published else None,
            link=link,
        )

    # --- Draft ------------------------------------------------------------------------

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
            return Refused("TITLE_REQUIRED", "the template needs a title")
        if kind not in ("HEALTH", "SHIP"):
            return Refused("INVALID_KIND", "Ground schedules HEALTH or SHIP tasks")
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
                return Refused("NOT_FOUND", f"template {template_id} does not exist")
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
                await repo.delete_item(draft.id, template_id)  # it only existed in the draft
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
                return Refused("NOT_FOUND", f"template {template_id} does not exist")
        return Ok(draft.version)

    async def _draft(self, repo: GroundlinkRepository) -> GroundPlanRow:
        draft = await repo.draft()
        if draft is None:
            await repo.create_draft(uuid4(), await repo.max_version() + 1)
            draft = await repo.draft()
        assert draft is not None
        return draft

    # --- Publishing and link ------------------------------------------------------------

    async def publish(self) -> GroundOutcome:
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            if any(in_flight(p.status) for p in await repo.plans()):
                return Refused("PLAN_IN_FLIGHT", "a published plan is awaiting confirmation")
            draft = await repo.draft()
            if draft is None or not await repo.items(draft.id):
                return Refused("NOTHING_TO_PUBLISH", "the draft has no changes")
            link = await repo.link()
            stage = "IN_TRANSIT" if link.online else "QUEUED"
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
            queued = await repo.plans(["QUEUED"])
            if online:
                for plan in queued:
                    await repo.set_status(plan.id, "IN_TRANSIT", only_from=["QUEUED"])
                # Held acknowledgements go up when the link returns.
                for plan in await repo.plans(["APPLIED"]):
                    await repo.set_status(plan.id, "CONFIRMED", only_from=["APPLIED"], at=now)
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
        """Delivers to the ship what was on the link. If the link went down, back to the queue."""
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            plan = await repo.plan(plan_id)
            if plan is None or plan.status != "IN_TRANSIT" or plan.batch_id is None:
                return
            if not (await repo.link()).online:
                await repo.set_status(plan_id, "QUEUED", only_from=["IN_TRANSIT"])
                return
            items = await repo.item_dicts(plan_id)
        received = await self._receiver.receive(
            plan.batch_id, plan.version, items, plan_hash(plan.version, items)
        )
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            if received.status == "received":
                await repo.set_status(plan_id, "RECEIVED", only_from=["IN_TRANSIT"])
            else:
                reason = received.reason or "the ship already has an equal or newer version"
                await repo.set_status(plan_id, "REJECTED", only_from=["IN_TRANSIT"], reason=reason)

    async def on_batch_acknowledged(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """The ship acknowledged the batch. If the link is down, the acknowledgement waits."""
        ack = event.payload_as(BatchAcknowledged)
        if ctx.session is None:
            raise RuntimeError("the Ground link needs the outbox relay session")
        repo = self._repo(ctx.session)
        plan = await repo.plan_by_batch(ack.batch_id)
        if plan is None:
            return
        if (await repo.link()).online:
            await repo.set_status(plan.id, "CONFIRMED", at=ack.acked_at)
        else:
            await repo.set_status(plan.id, "APPLIED")


def ship_template(
    template_id: UUID,
    title: str,
    kind: str,
    task_status: str | None,
    blocked_reason: str | None,
) -> ShipTemplate:
    """Status Ground sees, derived from the template's latest task on the ship."""
    status = task_status if task_status in ("COMPLETED", "BLOCKED") else "APPLIED"
    return ShipTemplate(template_id, title, kind, status, blocked_reason)
