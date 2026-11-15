from datetime import timedelta

import pytest
from sqlalchemy import text

from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.ingest_readings import UnknownSensors, ingest_readings
from spaceapp.modules.telemetry.contracts import ReadingsRecorded
from spaceapp.modules.telemetry.domain.readings import InvalidBatch, ReadingIn
from tests.integration.telemetry.conftest import AIR, CO2, HABITAT, LAB, O2, OTHER, T0, sensor

pytestmark = pytest.mark.integration


def at(seconds: int):  # type: ignore[no-untyped-def]
    return T0 + timedelta(seconds=seconds)


async def ingest(sf, readings, **kw):  # type: ignore[no-untyped-def]
    return await ingest_readings(sf, SqlTelemetryRepository, HABITAT, readings, **kw)


async def scalar(sf, sql: str):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (await s.execute(text(sql))).scalar_one()


async def events(sf):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (
            await s.execute(
                text(
                    "SELECT payload, partition_key, aggregate_type FROM platform.outbox_event ORDER BY id"
                )
            )
        ).all()


async def test_a_batch_is_stored_and_one_event_summarizes_it(session_factory, sensors):
    result = await ingest(
        session_factory,
        [
            ReadingIn(CO2, at(0), 0.7),
            ReadingIn(CO2, at(5), 0.9),
            ReadingIn(O2, at(5), 21.0, "ok"),
        ],
    )
    assert (result.accepted, result.duplicates) == (3, 0)
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.reading") == 3
    (ev,) = await events(session_factory)
    p = ReadingsRecorded.model_validate(ev.payload)
    assert p.habitat_id == HABITAT and p.batch_id == result.batch_id
    assert (p.ts_from, p.ts_to) == (at(0), at(5))
    latest = {x.sensor_id: (x.zone_id, x.metric, x.value) for x in p.latest}
    assert latest == {CO2: (LAB, "co2_mmhg", 0.9), O2: (LAB, "o2_pct", 21.0)}
    assert ev.partition_key == f"habitat:{HABITAT}" and ev.aggregate_type == "reading_batch"


async def test_sending_the_same_batch_twice_leaves_the_readings_once_and_one_event(
    session_factory, sensors
):
    batch = [ReadingIn(CO2, at(0), 0.7), ReadingIn(O2, at(0), 21.0)]
    first = await ingest(session_factory, batch)
    second = await ingest(session_factory, batch)
    assert (first.accepted, second.accepted, second.duplicates) == (2, 0, 2)
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.reading") == 2
    assert len(await events(session_factory)) == 1


async def test_a_partially_new_batch_reports_only_the_new_readings_in_the_event(
    session_factory, sensors
):
    await ingest(session_factory, [ReadingIn(CO2, at(0), 0.7)])
    result = await ingest(session_factory, [ReadingIn(CO2, at(0), 0.7), ReadingIn(CO2, at(5), 0.8)])
    assert (result.accepted, result.duplicates) == (1, 1)
    p = ReadingsRecorded.model_validate((await events(session_factory))[-1].payload)
    assert [x.value for x in p.latest] == [0.8] and p.ts_from == p.ts_to == at(5)


async def test_an_unknown_sensor_rejects_the_whole_batch_without_side_effects(
    session_factory, sensors
):
    ghost = sensor(OTHER, AIR, "x").id.__class__("00000000-0000-4000-8000-00000000dead")
    with pytest.raises(UnknownSensors) as err:
        await ingest(session_factory, [ReadingIn(CO2, at(0), 0.7), ReadingIn(ghost, at(0), 1.0)])
    assert err.value.sensor_ids == [ghost]
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.reading") == 0
    assert await events(session_factory) == []


async def test_a_batch_over_the_limit_is_rejected_before_touching_the_database(
    session_factory, sensors
):
    with pytest.raises(InvalidBatch, match="500"):
        await ingest(session_factory, [ReadingIn(CO2, at(i), 1.0) for i in range(501)])
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.reading") == 0


async def test_readings_of_new_days_create_their_daily_partitions(session_factory, sensors):
    far = T0.replace(year=2031, month=3, day=9)
    result = await ingest(
        session_factory, [ReadingIn(CO2, far, 1.0), ReadingIn(CO2, far + timedelta(days=1), 2.0)]
    )
    assert result.accepted == 2
    names = {r for r in (await _partitions(session_factory))}
    assert {"reading_20310309", "reading_20310310"} <= names
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.reading_default") == 0


async def _partitions(sf):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (
            (
                await s.execute(
                    text(
                        "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
                        "WHERE i.inhparent = 'telemetry.reading'::regclass"
                    )
                )
            )
            .scalars()
            .all()
        )


async def test_quality_flags_are_kept(session_factory, sensors):
    await ingest(session_factory, [ReadingIn(CO2, at(0), 0.7, "suspect")])
    assert await scalar(session_factory, "SELECT quality FROM telemetry.reading") == "suspect"


async def test_registering_sensors_twice_is_harmless(session_factory, sensors):
    async with session_factory() as s, s.begin():
        await SqlTelemetryRepository(s).register_sensors([sensor(CO2, LAB, "co2_mmhg", "mmHg")])
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.sensor") == 3
