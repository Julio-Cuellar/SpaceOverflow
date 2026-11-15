"""Servicio del simulador: registra sensores, genera lecturas por zona y controla escenarios."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.telemetry.application.ingest_readings import IngestResult, ingest_readings
from spaceapp.modules.telemetry.contracts import ScenarioChanged
from spaceapp.modules.telemetry.domain.layout import Layout
from spaceapp.modules.telemetry.domain.readings import ReadingIn, SensorInfo
from spaceapp.modules.telemetry.domain.simulator import SENSOR_SPECS, Simulator
from spaceapp.modules.telemetry.ports.repositories import TelemetryRepository
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.ids import sensor_id
from spaceapp.platform.outbox import UnitOfWork


class SimulationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: Callable[[AsyncSession], TelemetryRepository],
        layout: Layout,
        *,
        seed: int = 7,
        noise: bool = True,
    ) -> None:
        self._sf = session_factory
        self._repository = repository
        self._layout = layout
        self._sim = Simulator(layout.zones, seed=seed, noise=noise)

    async def ensure_sensors(self) -> None:
        sensors = [
            SensorInfo(
                sensor_id(self._layout.zone_id(z.code), metric),
                self._layout.habitat_id,
                self._layout.zone_id(z.code),
                None,
                "cabina",
                metric,
                unit,
                period,
                "SIMULATED",
            )
            for z in self._layout.zones
            for metric, unit, period in SENSOR_SPECS
        ]
        async with UnitOfWork(self._sf) as uow:
            await self._repository(uow.session).register_sensors(sensors)

    async def tick(self, now: datetime) -> IngestResult:
        due = self._sim.tick(now)
        if not due:
            return IngestResult(uuid4(), 0, 0)
        readings = [
            ReadingIn(sensor_id(self._layout.zone_id(r.zone_code), r.metric), r.ts, r.value)
            for r in due
        ]
        return await ingest_readings(self._sf, self._repository, self._layout.habitat_id, readings)

    async def start_scenario(
        self, key: str, zone: str | None, *, speed: float = 1.0, now: datetime | None = None
    ) -> None:
        at = now or datetime.now(UTC)
        self._sim.start(key, zone, speed=speed)
        zone_uuid = self._layout.zone_id(zone) if zone else None
        async with UnitOfWork(self._sf) as uow:
            if key != "normal":
                await self._repository(uow.session).start_scenario(
                    self._layout.habitat_id, zone_uuid, key, speed, at
                )
            await self._announce(uow, key, "started", speed, zone_uuid)

    async def stop_scenario(
        self, key: str, zone: str | None, *, now: datetime | None = None
    ) -> None:
        at = now or datetime.now(UTC)
        self._sim.stop(key, zone)
        zone_uuid = self._layout.zone_id(zone) if zone else None
        async with UnitOfWork(self._sf) as uow:
            await self._repository(uow.session).stop_scenario(
                self._layout.habitat_id, zone_uuid, key, at
            )
            await self._announce(uow, key, "stopped", 1.0, zone_uuid)

    async def _announce(
        self, uow: UnitOfWork, key: str, state: str, speed: float, zone_uuid: object
    ) -> None:
        await uow.publish(
            EventEnvelope.from_payload(
                ScenarioChanged(key=key, state=state, speed=speed, zone_id=zone_uuid),
                aggregate_type="scenario",
                aggregate_id=uuid4(),
                partition_key=f"habitat:{self._layout.habitat_id}",
            )
        )

    async def run_forever(self, stop: asyncio.Event, period_s: float = 1.0) -> None:
        """Una vuelta por segundo con el reloj real."""
        while not stop.is_set():
            await self.tick(datetime.now(UTC))
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=period_s)
