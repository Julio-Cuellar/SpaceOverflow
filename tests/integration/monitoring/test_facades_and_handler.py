from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.monitoring.adapters.inbound.events import register_monitoring
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.modules.monitoring.domain.series import Sample, within
from spaceapp.modules.monitoring.facade import ActiveAlertsQuery, RuleQuery
from spaceapp.modules.telemetry.contracts import LatestReading, ReadingsRecorded
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
H, Z = uuid4(), uuid4()
T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
BASE = {
    "pressure_kpa": 101.3,
    "o2_pct": 21.0,
    "co2_mmhg": 0.6,
    "temperature_c": 22.0,
    "humidity_pct": 45.0,
}


class FixedReadings:
    def __init__(self, **over: float) -> None:
        self.values = {**BASE, **over}

    async def series(self, zone_id: UUID, metrics, since, until):  # type: ignore[no-untyped-def]
        data = [Sample(T0 + timedelta(seconds=s), 0.0) for s in range(-200, 400)]
        return {
            m: within([Sample(x.ts, self.values[m]) for x in data], since, until) for m in metrics
        }


def batch(at: int) -> EventEnvelope:
    p = ReadingsRecorded(
        batch_id=uuid4(),
        habitat_id=H,
        ts_from=T0 + timedelta(seconds=at - 1),
        ts_to=T0 + timedelta(seconds=at),
        latest=[LatestReading(sensor_id=uuid4(), zone_id=Z, metric="co2_mmhg", value=3.5)],
    )
    return EventEnvelope.from_payload(
        p, aggregate_type="batch", aggregate_id=p.batch_id, partition_key=f"habitat:{H}"
    )


def relay_for(sf, readings: FixedReadings, **kw):  # type: ignore[no-untyped-def]
    reg = SubscriptionRegistry()
    handler = EvaluateReadings(
        CATALOG, lambda _s: readings, lambda s: SqlAlertRepository(s), window_scale=1 / 60, **kw
    )
    register_monitoring(reg, handler)
    return OutboxRelay(sf, reg)


async def publish(sf, e: EventEnvelope) -> None:  # type: ignore[no-untyped-def]
    async with UnitOfWork(sf) as uow:
        await uow.publish(e)


async def test_the_handler_runs_on_the_real_relay_and_stores_alert_and_event_together(
    session_factory,
):
    relay = relay_for(session_factory, FixedReadings(co2_mmhg=3.5))
    await publish(session_factory, batch(100))
    await relay.run_once()
    async with session_factory() as s:
        alerts = (await s.execute(text("SELECT rule_id, status FROM monitoring.alert"))).all()
        types = (
            (await s.execute(text("SELECT type FROM platform.outbox_event ORDER BY id")))
            .scalars()
            .all()
        )
    assert len(alerts) == 1 and alerts[0].status == "raised"
    assert types == ["telemetry.readings_recorded", "monitoring.alert_raised"]


async def test_a_repeated_delivery_of_the_same_event_does_not_duplicate_the_alert(session_factory):
    relay = relay_for(session_factory, FixedReadings(co2_mmhg=3.5))
    e = batch(100)
    await publish(session_factory, e)
    await relay.run_once()
    async with session_factory() as s, s.begin():  # the same event is left pending again
        await s.execute(
            text("UPDATE platform.outbox_event SET status='pending' WHERE event_id=:i"),
            {"i": e.event_id},
        )
    await relay.run_once()
    async with session_factory() as s:
        n = (await s.execute(text("SELECT count(*) FROM monitoring.alert"))).scalar_one()
    assert n == 1


async def test_a_later_batch_with_the_same_condition_keeps_a_single_alert(session_factory):
    relay = relay_for(session_factory, FixedReadings(co2_mmhg=3.5))
    for at in (100, 101, 102):
        await publish(session_factory, batch(at))
    await relay.run_once()
    async with session_factory() as s:
        n = (await s.execute(text("SELECT count(*) FROM monitoring.alert"))).scalar_one()
        raised = (
            await s.execute(
                text(
                    "SELECT count(*) FROM platform.outbox_event "
                    "WHERE type='monitoring.alert_raised'"
                )
            )
        ).scalar_one()
    assert n == 1 and raised == 1


async def test_active_alerts_query_lists_what_other_modules_need(session_factory):
    relay = relay_for(session_factory, FixedReadings(co2_mmhg=3.5))
    await publish(session_factory, batch(100))
    await relay.run_once()
    views = await ActiveAlertsQuery(session_factory).list(zone_id=Z)
    assert [(v.rule_key, v.zone_id, v.severity, v.status, v.evidence_state) for v in views] == [
        ("env-co2-1h", Z, "alert", "raised", "VERIFIED")
    ]
    assert await ActiveAlertsQuery(session_factory).list(zone_id=uuid4()) == []
    assert len(await ActiveAlertsQuery(session_factory).list(habitat_id=H)) == 1


def test_rule_query_gives_the_rule_and_its_action_without_touching_the_database():
    q = RuleQuery(CATALOG)
    v = q.get("env-co2-1h")
    assert v is not None
    assert (v.action_key, v.source_requirement, v.evidence_state) == (
        "check_ventilation_and_filters",
        "V2 6004",
        "VERIFIED",
    )
    assert q.get("no-existe") is None
