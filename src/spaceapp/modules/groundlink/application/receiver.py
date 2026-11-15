"""Ship side: receives Ground plans (R9) and acknowledges once Missions applied them."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.engagement.contracts import GroundPlanApplied
from spaceapp.modules.groundlink.contracts import (
    BatchAcknowledged,
    GroundPlanReceived,
    PlanChange,
)
from spaceapp.modules.groundlink.domain.plans import inbound_decision
from spaceapp.modules.groundlink.ports import GroundlinkRepository
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import UnitOfWork

CONSUMER_APPLIED = "groundlink.on_ground_plan_applied"

RepositoryFactory = Callable[[AsyncSession], GroundlinkRepository]


@dataclass(frozen=True)
class Received:
    status: str  # received, ignored, rejected
    reason: str | None = None


class PlanReceiver:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: RepositoryFactory,
        habitat_id: UUID,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sf = session_factory
        self._repo = repository
        self._habitat = habitat_id
        self._clock = clock

    async def receive(
        self,
        batch_id: UUID,
        plan_version: int,
        items: Sequence[Mapping[str, Any]],
        payload_hash: str,
    ) -> Received:
        try:
            changes = [PlanChange.model_validate(i) for i in items]
        except ValidationError as exc:
            return Received("rejected", f"an item is malformed: {exc.errors()[0]['msg']}")
        now = self._clock()
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            decision, reason = inbound_decision(
                plan_version, items, payload_hash, last_version=await repo.last_inbound_version()
            )
            if decision == "ignored":
                return Received("ignored")
            status = "RECEIVED" if decision == "received" else "REJECTED"
            fresh = await repo.save_inbound(
                batch_id=batch_id,
                plan_version=plan_version,
                status=status,
                payload_hash=payload_hash,
                reason=reason,
                at=now,
            )
            if decision == "rejected":
                return Received("rejected", reason)
            if not fresh:
                return Received("ignored")  # the same batch, delivered again
            await uow.publish(
                EventEnvelope.from_payload(
                    GroundPlanReceived(
                        batch_id=batch_id, plan_version=plan_version, changes=changes
                    ),
                    aggregate_type="ground_plan",
                    aggregate_id=batch_id,
                    partition_key=f"habitat:{self._habitat}",
                )
            )
        return Received("received")

    async def on_plan_applied(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """Missions applied the plan: it is marked and the batch is acknowledged to Ground."""
        applied = event.payload_as(GroundPlanApplied)
        if ctx.session is None:
            raise RuntimeError("the Ground link needs the outbox relay session")
        repo = self._repo(ctx.session)
        rejected = [r.model_dump() for r in applied.rejected]
        batch_id = await repo.mark_inbound_applied(
            applied.plan_version, rejected, event.occurred_at
        )
        if batch_id is None:
            return
        await ctx.publish(
            EventEnvelope.from_payload(
                BatchAcknowledged(
                    batch_id=batch_id,
                    items=len(applied.applied) + len(applied.rejected),
                    acked_at=event.occurred_at,
                ),
                aggregate_type="ground_plan",
                aggregate_id=batch_id,
                partition_key=event.partition_key,
                correlation_id=event.correlation_id or event.event_id,
                causation_id=event.event_id,
            )
        )
