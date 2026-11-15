from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.modules.telemetry.contracts import ReadingsRecorded, ScenarioChanged
from spaceapp.modules.telemetry.domain.simulator import UnknownZone
from spaceapp.platform.ids import zone_id
from tests.integration.telemetry.conftest import T0

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
LAYOUT = load_layout(ROOT / "data" / "telemetry" / "sim_layout.json")


def service(sf) -> SimulationService:  # type: ignore[no-untyped-def]
    return SimulationService(sf, SqlTelemetryRepository, LAYOUT, seed=7)


async def scalar(sf, sql: str):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (await s.execute(text(sql))).scalar_one()


async def events(sf, kind: str):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (
            await s.execute(
                text("SELECT payload FROM platform.outbox_event WHERE type = :t ORDER BY id"),
                {"t": kind},
            )
        ).all()


def test_the_layout_describes_ten_zones_with_stable_ids():
    assert [z.code for z in LAYOUT.zones] == [
        "eng",
        "eclss",
        "lab",
        "med",
        "bridge",
        "air",
        "store",
        "gym",
        "galley",
        "crew",
    ]
    assert LAYOUT.habitat_code == "transit-ship"
    assert LAYOUT.zone_id("lab") == zone_id("transit-ship", "lab")


async def test_ensure_sensors_registers_five_simulated_sensors_per_zone_once(session_factory):
    svc = service(session_factory)
    await svc.ensure_sensors()
    await svc.ensure_sensors()
    assert await scalar(session_factory, "SELECT count(*) FROM telemetry.sensor") == 50
    assert (
        await scalar(
            session_factory, "SELECT count(*) FROM telemetry.sensor WHERE origin <> 'SIMULATED'"
        )
        == 0
    )
    assert (
        await scalar(
            session_factory,
            "SELECT sample_period_s FROM telemetry.sensor WHERE metric = 'pressure_kpa' LIMIT 1",
        )
        == 1
    )
    assert (
        await scalar(
            session_factory,
            "SELECT DISTINCT sample_period_s FROM telemetry.sensor WHERE metric = 'co2_mmhg'",
        )
        == 5
    )
    assert (
        await scalar(
            session_factory,
            "SELECT DISTINCT sample_period_s FROM telemetry.sensor WHERE metric = 'humidity_pct'",
        )
        == 60
    )


async def test_a_tick_ingests_what_is_due_and_emits_one_event(session_factory):
    svc = service(session_factory)
    await svc.ensure_sensors()
    first = await svc.tick(T0)
    second = await svc.tick(T0 + timedelta(seconds=1))
    assert (first.accepted, second.accepted) == (50, 10)  # at the second, only the pressure
    payloads = [
        ReadingsRecorded.model_validate(e.payload)
        for e in await events(session_factory, "telemetry.readings_recorded")
    ]
    assert [len(p.latest) for p in payloads] == [50, 10]
    assert {x.metric for x in payloads[1].latest} == {"pressure_kpa"}


async def test_a_tick_with_nothing_due_does_nothing(session_factory):
    svc = service(session_factory)
    await svc.ensure_sensors()
    await svc.tick(T0)
    again = await svc.tick(T0)
    assert again.accepted == 0
    assert (
        await scalar(
            session_factory,
            "SELECT count(*) FROM platform.outbox_event WHERE type='telemetry.readings_recorded'",
        )
        == 1
    )


async def test_starting_and_stopping_a_scenario_is_recorded_and_announced(session_factory):
    svc = service(session_factory)
    await svc.start_scenario("co2_slow", "lab", speed=2.0, now=T0)
    row = (await _runs(session_factory))[0]
    assert (row.scenario_key, row.state, float(row.speed), row.zone_id) == (
        "co2_slow",
        "started",
        2.0,
        zone_id("transit-ship", "lab"),
    )
    await svc.stop_scenario("co2_slow", "lab", now=T0 + timedelta(seconds=30))
    row = (await _runs(session_factory))[0]
    assert row.state == "stopped" and row.stopped_at == T0 + timedelta(seconds=30)
    states = [
        ScenarioChanged.model_validate(e.payload).state
        for e in await events(session_factory, "telemetry.scenario_changed")
    ]
    assert states == ["started", "stopped"]


async def _runs(sf):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (await s.execute(text("SELECT * FROM telemetry.scenario_run"))).all()


async def test_an_unknown_zone_is_refused_without_side_effects(session_factory):
    with pytest.raises(UnknownZone):
        await service(session_factory).start_scenario("co2_slow", "narnia", now=T0)
    assert await _runs(session_factory) == []
