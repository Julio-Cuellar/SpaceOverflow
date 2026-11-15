from datetime import UTC, datetime
from uuid import UUID

import pytest

from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.domain.readings import SensorInfo
from spaceapp.platform.ids import DEFAULT_HABITAT_CODE, habitat_id, sensor_id, zone_id

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
HABITAT = habitat_id(DEFAULT_HABITAT_CODE)
LAB = zone_id(DEFAULT_HABITAT_CODE, "lab")
AIR = zone_id(DEFAULT_HABITAT_CODE, "air")
CO2 = sensor_id(LAB, "co2_mmhg")
O2 = sensor_id(LAB, "o2_pct")
OTHER = sensor_id(AIR, "co2_mmhg")


def sensor(sid: UUID, zone: UUID, metric: str, unit: str = "u", period: int = 5) -> SensorInfo:
    return SensorInfo(sid, HABITAT, zone, None, "cabina", metric, unit, period, "SIMULATED")


@pytest.fixture
async def sensors(session_factory):  # type: ignore[no-untyped-def]
    async with session_factory() as s, s.begin():
        await SqlTelemetryRepository(s).register_sensors(
            [
                sensor(CO2, LAB, "co2_mmhg", "mmHg"),
                sensor(O2, LAB, "o2_pct", "%"),
                sensor(OTHER, AIR, "co2_mmhg", "mmHg"),
            ]
        )
