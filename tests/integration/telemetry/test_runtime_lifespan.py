import asyncio

import httpx
import pytest
from sqlalchemy import text

from spaceapp.main import create_app
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.platform.config import Settings
from tests.integration.telemetry.conftest import CO2, HABITAT, LAB, T0, sensor

pytestmark = pytest.mark.integration


async def test_with_the_relay_enabled_an_ingested_batch_ends_up_in_the_rollup(
    session_factory, async_url, listen_dsn
):
    async with session_factory() as s, s.begin():
        await SqlTelemetryRepository(s).register_sensors([sensor(CO2, LAB, "co2_mmhg", "mmHg")])
    settings = Settings(database_url=async_url, relay_enabled=True)
    app = create_app(settings, session_factory=session_factory)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://t"
        ) as c:
            r = await c.post(
                "/api/v1/telemetry/readings",
                json={
                    "habitat_id": str(HABITAT),
                    "readings": [{"sensor_id": str(CO2), "ts": T0.isoformat(), "value": 2.5}],
                },
            )
            assert r.status_code == 202
        rows = []
        for _ in range(40):
            async with session_factory() as s:
                rows = (await s.execute(text("SELECT n FROM telemetry.reading_rollup_1m"))).all()
            if rows:
                break
            await asyncio.sleep(0.1)
    assert [r.n for r in rows] == [1]


async def test_with_the_relay_disabled_nothing_is_consumed_in_the_background(session_factory):
    app = create_app(Settings(), session_factory=session_factory)
    async with app.router.lifespan_context(app):
        assert app.state.relay_task is None and app.state.simulator_task is None
