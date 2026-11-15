"""Caso de uso: guardar un lote de lecturas de forma idempotente y anunciarlo con un evento."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.telemetry.contracts import LatestReading, ReadingsRecorded
from spaceapp.modules.telemetry.domain.readings import ReadingIn, validate_batch
from spaceapp.modules.telemetry.ports.repositories import TelemetryRepository
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import UnitOfWork


@dataclass(frozen=True)
class IngestResult:
    batch_id: UUID
    accepted: int
    duplicates: int


class UnknownSensors(Exception):
    def __init__(self, sensor_ids: list[UUID]) -> None:
        super().__init__(f"sensores desconocidos: {', '.join(map(str, sensor_ids))}")
        self.sensor_ids = sensor_ids


async def ingest_readings(
    session_factory: async_sessionmaker[AsyncSession],
    repository: Callable[[AsyncSession], TelemetryRepository],
    habitat_id: UUID,
    readings: Sequence[ReadingIn],
    *,
    batch_id: UUID | None = None,
) -> IngestResult:
    validate_batch(readings)
    batch_id = batch_id or uuid4()
    async with UnitOfWork(session_factory) as uow:
        repo = repository(uow.session)
        known = await repo.sensors_by_id({r.sensor_id for r in readings})
        missing = sorted(
            {
                r.sensor_id
                for r in readings
                if r.sensor_id not in known or known[r.sensor_id].habitat_id != habitat_id
            },
            key=str,
        )
        if missing:
            raise UnknownSensors(missing)
        await repo.ensure_partitions({r.ts.astimezone(UTC).date() for r in readings})
        inserted = await repo.insert_readings(readings)
        accepted = len(inserted)
        if accepted:
            value_of = {(r.sensor_id, r.ts): r.value for r in readings}
            newest: dict[UUID, tuple[object, float]] = {}
            for sensor_id, ts in inserted:
                if sensor_id not in newest or ts > newest[sensor_id][0]:  # type: ignore[operator]
                    newest[sensor_id] = (ts, value_of[(sensor_id, ts)])
            stamps = [ts for _, ts in inserted]
            await uow.publish(
                EventEnvelope.from_payload(
                    ReadingsRecorded(
                        batch_id=batch_id,
                        habitat_id=habitat_id,
                        ts_from=min(stamps),
                        ts_to=max(stamps),
                        latest=[
                            LatestReading(
                                sensor_id=sid,
                                zone_id=known[sid].zone_id,
                                metric=known[sid].metric,
                                value=v,
                            )
                            for sid, (_, v) in newest.items()
                        ],
                    ),
                    aggregate_type="reading_batch",
                    aggregate_id=batch_id,
                    partition_key=f"habitat:{habitat_id}",
                )
            )
    return IngestResult(batch_id, accepted, len(readings) - accepted)
