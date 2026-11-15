from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.telemetry.adapters.inbound.events import register_telemetry
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.ingest_readings import ingest_readings
from spaceapp.modules.telemetry.application.rollup import RecomputeRollup
from spaceapp.modules.telemetry.domain.readings import ReadingIn
from spaceapp.modules.telemetry.facade import SqlReadingQuery
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.outbox import OutboxRelay
from tests.integration.telemetry.conftest import CO2, HABITAT, LAB, O2, T0

pytestmark = pytest.mark.integration


def at(seconds: int):  # type: ignore[no-untyped-def]
    return T0 + timedelta(seconds=seconds)


def make_relay(sf):  # type: ignore[no-untyped-def]
    reg = SubscriptionRegistry()
    register_telemetry(reg, RecomputeRollup(lambda s: SqlTelemetryRepository(s)))
    return OutboxRelay(sf, reg)


async def ingest(sf, readings):  # type: ignore[no-untyped-def]
    return await ingest_readings(sf, SqlTelemetryRepository, HABITAT, readings)


async def rollup(sf):  # type: ignore[no-untyped-def]
    async with sf() as s:
        rows = (
            await s.execute(
                text(
                    "SELECT sensor_id, bucket, avg_v, min_v, max_v, n FROM telemetry.reading_rollup_1m "
                    "ORDER BY sensor_id, bucket"
                )
            )
        ).all()
    return {(r.sensor_id, r.bucket): (r.avg_v, r.min_v, r.max_v, r.n) for r in rows}


async def test_the_handler_builds_one_minute_buckets(session_factory, sensors):
    await ingest(
        session_factory,
        [ReadingIn(CO2, at(10), 1.0), ReadingIn(CO2, at(40), 3.0), ReadingIn(CO2, at(65), 5.0)],
    )
    await make_relay(session_factory).run_once()
    got = await rollup(session_factory)
    assert got[(CO2, at(0))] == (2.0, 1.0, 3.0, 2)
    assert got[(CO2, at(60))] == (5.0, 5.0, 5.0, 1)


async def test_recomputing_is_idempotent_and_picks_up_late_readings(session_factory, sensors):
    relay = make_relay(session_factory)
    await ingest(session_factory, [ReadingIn(CO2, at(10), 1.0)])
    await relay.run_once()
    async with session_factory() as s, s.begin():  # repeated delivery of the same event
        await s.execute(text("UPDATE platform.outbox_event SET status='pending'"))
    await relay.run_once()
    assert (await rollup(session_factory))[(CO2, at(0))] == (1.0, 1.0, 1.0, 1)
    await ingest(
        session_factory, [ReadingIn(CO2, at(50), 3.0)]
    )  # another reading of the same minute arrives
    await relay.run_once()
    assert (await rollup(session_factory))[(CO2, at(0))] == (2.0, 1.0, 3.0, 2)


async def test_series_returns_the_samples_of_a_zone_by_metric_in_range(session_factory, sensors):
    await ingest(
        session_factory,
        [
            ReadingIn(CO2, at(0), 0.7),
            ReadingIn(CO2, at(5), 0.9),
            ReadingIn(CO2, at(50), 2.0),
            ReadingIn(O2, at(5), 21.0),
        ],
    )
    async with session_factory() as s:
        got = await SqlReadingQuery(s).series(
            LAB, ["co2_mmhg", "o2_pct", "humidity_pct"], at(0), at(10)
        )
        none = await SqlReadingQuery(s).series(uuid4(), ["co2_mmhg"], at(0), at(10))
    assert [(x.ts, x.value) for x in got["co2_mmhg"]] == [(at(0), 0.7), (at(5), 0.9)]
    assert [x.value for x in got["o2_pct"]] == [21.0] and got["humidity_pct"] == []
    assert none == {"co2_mmhg": []}


async def test_rollup_mean_weights_each_minute_by_its_sample_count(session_factory, sensors):
    await ingest(
        session_factory,
        [ReadingIn(CO2, at(10), 1.0), ReadingIn(CO2, at(40), 3.0), ReadingIn(CO2, at(65), 5.0)],
    )
    await make_relay(session_factory).run_once()
    async with session_factory() as s:
        q = SqlReadingQuery(s)
        mean = await q.rollup_mean(LAB, "co2_mmhg", window_s=120, until=at(119))
        empty = await q.rollup_mean(LAB, "co2_mmhg", window_s=60, until=at(3000))
    assert mean == pytest.approx(3.0)  # (1 + 3 + 5) / 3
    assert empty is None
