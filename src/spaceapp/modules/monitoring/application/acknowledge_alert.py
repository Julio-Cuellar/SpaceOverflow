"""Use case: the crew acknowledges an alert. Idempotent."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.monitoring.contracts import AlertAcknowledged
from spaceapp.modules.monitoring.domain.lifecycle import ack_decision
from spaceapp.modules.monitoring.ports.repositories import AlertRepository
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import UnitOfWork


@dataclass(frozen=True)
class Acknowledged:
    alert_id: UUID


@dataclass(frozen=True)
class AlreadyAcknowledged:
    alert_id: UUID


@dataclass(frozen=True)
class AlertAlreadyResolved:
    alert_id: UUID


@dataclass(frozen=True)
class AlertNotFound:
    pass


AckResult = Acknowledged | AlreadyAcknowledged | AlertAlreadyResolved | AlertNotFound


async def acknowledge_alert(
    session_factory: async_sessionmaker[AsyncSession],
    repository: Callable[[AsyncSession], AlertRepository],
    alert_id: UUID,
    crew_member_id: UUID,
    *,
    note: str | None = None,
    now: datetime | None = None,
) -> AckResult:
    at = now or datetime.now(UTC)
    async with UnitOfWork(session_factory) as uow:
        repo = repository(uow.session)
        record = await repo.get(alert_id)
        if record is None:
            return AlertNotFound()
        decision = ack_decision(record.status)
        if decision == "resolved":
            return AlertAlreadyResolved(alert_id)
        if decision == "already":
            return AlreadyAcknowledged(alert_id)
        await repo.acknowledge(alert_id, crew_member_id, note, at)
        await uow.publish(
            EventEnvelope.from_payload(
                AlertAcknowledged(alert_id=alert_id, crew_member_id=crew_member_id, at=at),
                aggregate_type="alert",
                aggregate_id=alert_id,
                partition_key=f"habitat:{record.habitat_id}",
            )
        )
        return Acknowledged(alert_id)
