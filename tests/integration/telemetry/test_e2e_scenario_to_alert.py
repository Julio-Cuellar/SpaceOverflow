"""From a simulated scenario to the alert, with the real relay, handlers and PostgreSQL."""

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from spaceapp.modules.monitoring.adapters.inbound.events import register_monitoring
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.adapters.outbound.telemetry_readings import TelemetryReadings
from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.modules.telemetry.adapters.inbound.events import register_telemetry
from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.rollup import RecomputeRollup
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.outbox import OutboxRelay
from tests.integration.telemetry.conftest import T0

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
LAYOUT = load_layout(ROOT / "data" / "telemetry" / "sim_layout.json")


async def drain(relay: OutboxRelay) -> None:
    while await relay.run_once():
        pass


async def run_scenario(sf, scenario: str, zone: str, start_at: int, until: int):  # type: ignore[no-untyped-def]
    reg = SubscriptionRegistry()
    register_telemetry(reg, RecomputeRollup(lambda s: SqlTelemetryRepository(s)))
    handler = EvaluateReadings(
        CATALOG,
        lambda s: TelemetryReadings(s),
        lambda s: SqlAlertRepository(s),
        window_scale=1 / 60,
        hysteresis=3,
    )
    register_monitoring(reg, handler)
    relay = OutboxRelay(sf, reg)
    svc = SimulationService(sf, SqlTelemetryRepository, LAYOUT, seed=7)
    await svc.ensure_sensors()
    for step in range(0, until + 1, 5):
        now = T0 + timedelta(seconds=step)
        if step == start_at:
            await svc.start_scenario(scenario, zone, now=now)
        await svc.tick(now)
        await drain(relay)
    async with sf() as s:
        return (
            await s.execute(
                text(
                    "SELECT r.key, a.zone_id, a.severity, a.status, a.raised_at FROM monitoring.alert a "
                    "JOIN monitoring.rule r ON r.id = a.rule_id ORDER BY a.raised_at, r.key"
                )
            )
        ).all()


async def test_a_slow_co2_scenario_warns_first_and_then_raises_the_verified_alert(session_factory):
    alerts = await run_scenario(session_factory, "co2_slow", "lab", start_at=150, until=330)
    lab = LAYOUT.zone_id("lab")
    keys = [a.key for a in alerts]
    assert all(a.zone_id == lab for a in alerts)  # no other zone was altered
    assert "env-trend-co2" in keys and "env-co2-1h" in keys
    assert keys.index("env-trend-co2") < keys.index("env-co2-1h")  # the trend first
    final = next(a for a in alerts if a.key == "env-co2-1h")
    assert (final.severity, final.status) == ("alert", "raised")


async def test_a_normal_run_raises_no_alerts_at_all(session_factory):
    assert await run_scenario(session_factory, "normal", "lab", start_at=-1, until=300) == []


async def test_a_pressure_leak_raises_the_rate_rule_and_low_oxygen(session_factory):
    reg = SubscriptionRegistry()
    handler = EvaluateReadings(
        CATALOG,
        lambda s: TelemetryReadings(s),
        lambda s: SqlAlertRepository(s),
        window_scale=1 / 60,
    )
    register_monitoring(reg, handler)
    relay = OutboxRelay(session_factory, reg)
    svc = SimulationService(session_factory, SqlTelemetryRepository, LAYOUT, seed=7)
    await svc.ensure_sensors()
    await svc.start_scenario("pressure_leak", "air", now=T0)
    for step in range(0, 61):
        await svc.tick(T0 + timedelta(seconds=step))
        await drain(relay)
    async with session_factory() as s:
        keys = set(
            (
                await s.execute(
                    text(
                        "SELECT r.key FROM monitoring.alert a JOIN monitoring.rule r ON r.id = a.rule_id"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert "env-dpdt" in keys
    assert keys & {"env-pio2-low", "env-pio2-abs-low"}
