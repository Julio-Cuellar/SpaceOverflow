from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from spaceapp.modules.telemetry.domain.readings import ReadingIn, SensorInfo


class TelemetryRepository(Protocol):
    async def register_sensors(self, sensors: Sequence[SensorInfo]) -> None: ...

    async def sensors_by_id(self, ids: Iterable[UUID]) -> dict[UUID, SensorInfo]: ...

    async def ensure_partitions(self, days: Iterable[date]) -> None: ...

    async def insert_readings(
        self, readings: Sequence[ReadingIn]
    ) -> list[tuple[UUID, datetime]]: ...

    async def recompute_rollup(self, ts_from: datetime, ts_to: datetime) -> None: ...

    async def start_scenario(
        self, habitat_id: UUID, zone_id: UUID | None, key: str, speed: float, at: datetime
    ) -> None: ...

    async def stop_scenario(
        self, habitat_id: UUID, zone_id: UUID | None, key: str, at: datetime
    ) -> None: ...
