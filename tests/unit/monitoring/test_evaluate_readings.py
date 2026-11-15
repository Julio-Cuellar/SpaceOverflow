from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from spaceapp.modules.monitoring.adapters.inbound.events import register_monitoring
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.memory import InMemoryAlertRepository
from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.modules.monitoring.contracts import AlertRaised, AlertResolved
from spaceapp.modules.monitoring.domain.series import Sample, within
from spaceapp.modules.telemetry.contracts import LatestReading, ReadingsRecorded
from spaceapp.platform.bus import InMemoryEventBus
from spaceapp.platform.events import EventEnvelope

ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
HABITAT, ZONE, OTHER = uuid4(), uuid4(), uuid4()
T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
METRICS = {
    "pressure_kpa": 101.3,
    "o2_pct": 21.0,
    "co2_mmhg": 0.6,
    "temperature_c": 22.0,
    "humidity_pct": 45.0,
}


class FakeReadings:
    """Fuente de lecturas en memoria: un valor por metrica y por segundo hasta `now`."""

    def __init__(self) -> None:
        self.values: dict[UUID, dict[str, float]] = {}

    def set(self, zone: UUID, **over: float) -> None:
        self.values[zone] = {**METRICS, **self.values.get(zone, {}), **over}

    async def series(self, zone_id, metrics, since, until):  # type: ignore[no-untyped-def]
        out = {}
        for m in metrics:
            v = self.values.get(zone_id, METRICS)[m]
            data = [Sample(T0 + timedelta(seconds=s), v) for s in range(-200, 4000)]
            out[m] = within(data, since, until)
        return out


def setup(scale: float = 1 / 60, hysteresis: int = 3):  # type: ignore[no-untyped-def]
    bus, readings, repo = InMemoryEventBus(), FakeReadings(), InMemoryAlertRepository()
    handler = EvaluateReadings(
        CATALOG, lambda _s: readings, lambda _s: repo, window_scale=scale, hysteresis=hysteresis
    )
    register_monitoring(bus, handler)
    published: list[EventEnvelope] = []

    async def spy(e: EventEnvelope, ctx):  # type: ignore[no-untyped-def]
        published.append(e)

    bus.subscribe("monitoring.alert_raised", "spy", spy)
    bus.subscribe("monitoring.alert_resolved", "spy", spy)
    return bus, readings, repo, published


def readings_event(zone: UUID | None, at: int) -> EventEnvelope:
    p = ReadingsRecorded(
        batch_id=uuid4(),
        habitat_id=HABITAT,
        ts_from=T0 + timedelta(seconds=at - 1),
        ts_to=T0 + timedelta(seconds=at),
        latest=[LatestReading(sensor_id=uuid4(), zone_id=zone, metric="co2_mmhg", value=1.0)],
    )
    return EventEnvelope.from_payload(
        p, aggregate_type="batch", aggregate_id=p.batch_id, partition_key=f"habitat:{HABITAT}"
    )


async def test_a_high_co2_batch_raises_one_alert_with_its_evidence_and_ids():
    bus, readings, _, published = setup()
    readings.set(ZONE, co2_mmhg=3.5)
    e = readings_event(ZONE, 100)
    await bus.publish(e)
    raised = [x for x in published if x.type == "monitoring.alert_raised"]
    assert len(raised) == 1
    p = raised[0].payload_as(AlertRaised)
    assert (p.rule_key, p.zone_id, p.severity, p.cause_hint) == (
        "env-co2-1h",
        ZONE,
        "alerta",
        "AMBIENTE",
    )
    assert p.evidence["value"] == 3.5 and p.evidence["source_requirement"] == "V2 6004"
    assert raised[0].partition_key == f"habitat:{HABITAT}"
    assert raised[0].causation_id == e.event_id
    assert raised[0].aggregate_type == "alert" and raised[0].aggregate_id == p.alert_id


async def test_the_same_condition_in_later_batches_does_not_raise_again():
    bus, readings, _, published = setup()
    readings.set(ZONE, co2_mmhg=3.5)
    for at in (100, 101, 102):
        await bus.publish(readings_event(ZONE, at))
    assert len([x for x in published if x.type == "monitoring.alert_raised"]) == 1


async def test_the_alert_resolves_after_enough_clean_batches_with_its_duration():
    bus, readings, repo, published = setup(hysteresis=3)
    readings.set(ZONE, co2_mmhg=3.5)
    await bus.publish(readings_event(ZONE, 100))
    readings.set(ZONE, co2_mmhg=0.6)
    for at in (130, 131):
        await bus.publish(readings_event(ZONE, at))
    assert not [x for x in published if x.type == "monitoring.alert_resolved"]
    await bus.publish(readings_event(ZONE, 132))
    resolved = [x for x in published if x.type == "monitoring.alert_resolved"]
    assert len(resolved) == 1
    assert resolved[0].payload_as(AlertResolved).duration_s == 32
    assert await repo.active_for_zone(HABITAT, ZONE) == []


async def test_a_worse_band_replaces_the_milder_alert_right_away():
    bus, readings, _, published = setup()
    readings.set(ZONE, o2_pct=18.0)
    await bus.publish(readings_event(ZONE, 100))
    readings.set(ZONE, o2_pct=17.0)
    await bus.publish(readings_event(ZONE, 101))
    kinds = [(x.type, x.payload.get("rule_key")) for x in published]
    assert ("monitoring.alert_raised", "env-pio2-low-pre") in kinds
    # Con la ventana escalada, 121 mmHg ya cumple el límite absoluto (122), que es el más grave.
    assert ("monitoring.alert_raised", "env-pio2-abs-low") in kinds
    resolved = [x for x in published if x.type == "monitoring.alert_resolved"]
    assert len(resolved) == 1  # la banda leve se resuelve de inmediato, sin histéresis


async def test_alerts_of_different_zones_are_independent():
    bus, readings, repo, published = setup()
    readings.set(ZONE, co2_mmhg=3.5)
    readings.set(OTHER)
    await bus.publish(readings_event(ZONE, 100))
    await bus.publish(readings_event(OTHER, 100))
    raised = [x.payload_as(AlertRaised) for x in published if x.type == "monitoring.alert_raised"]
    assert [p.zone_id for p in raised] == [ZONE]
    assert await repo.active_for_zone(HABITAT, OTHER) == []


async def test_readings_without_a_zone_are_ignored_without_error():
    bus, _, _, published = setup()
    await bus.publish(readings_event(None, 100))
    assert published == []


async def test_one_batch_with_several_zones_evaluates_each_of_them():
    bus, readings, _, published = setup()
    readings.set(ZONE, co2_mmhg=3.5)
    readings.set(OTHER, humidity_pct=82.0)
    p = ReadingsRecorded(
        batch_id=uuid4(),
        habitat_id=HABITAT,
        ts_from=T0,
        ts_to=T0 + timedelta(seconds=100),
        latest=[
            LatestReading(sensor_id=uuid4(), zone_id=z, metric="co2_mmhg", value=1.0)
            for z in (ZONE, OTHER)
        ],
    )
    await bus.publish(
        EventEnvelope.from_payload(
            p, aggregate_type="batch", aggregate_id=p.batch_id, partition_key="h"
        )
    )
    zones = {x.payload["zone_id"] for x in published if x.type == "monitoring.alert_raised"}
    assert zones == {str(ZONE), str(OTHER)}
