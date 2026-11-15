"""El gateway se suscribe al bus y reparte lo que traduce."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.modules.realtime.adapters.inbound.events import RealtimeEvents, register_realtime
from spaceapp.modules.realtime.application.hub import Hub
from spaceapp.modules.telemetry.contracts import LatestReading, ReadingsRecorded
from spaceapp.platform.bus import InMemoryEventBus
from spaceapp.platform.events import EventEnvelope


def alert_event() -> EventEnvelope:
    aid = uuid4()
    return EventEnvelope.from_payload(
        AlertRaised(alert_id=aid, zone_id=None, rule_key="r", severity="alerta", evidence={}),
        aggregate_type="alert",
        aggregate_id=aid,
        partition_key="p",
    )


async def test_an_alert_reaches_the_clients_with_the_outbox_id_as_seq() -> None:
    calls: list[UUID] = []

    async def seq_of(session: AsyncSession | None, event_id: UUID) -> int | None:
        calls.append(event_id)
        return 42

    hub, bus = Hub(), InMemoryEventBus()
    register_realtime(bus, RealtimeEvents(hub, seq_of))
    client = hub.connect()
    event = alert_event()
    await bus.publish(event)
    (msg,) = client.queue.drain()
    assert (msg.seq, msg.type) == (42, "alert.raised")
    assert calls == [event.event_id]


async def test_ticks_have_no_seq_and_do_not_query_the_outbox() -> None:
    async def seq_of(session: AsyncSession | None, event_id: UUID) -> int | None:
        raise AssertionError("los ticks no consultan el outbox")

    hub, bus = Hub(), InMemoryEventBus()
    register_realtime(bus, RealtimeEvents(hub, seq_of))
    client = hub.connect()
    now = datetime.now(UTC)
    payload = ReadingsRecorded(
        batch_id=uuid4(),
        habitat_id=uuid4(),
        ts_from=now,
        ts_to=now,
        latest=[LatestReading(sensor_id=uuid4(), zone_id=None, metric="co2", value=0.5)],
    )
    await bus.publish(
        EventEnvelope.from_payload(
            payload, aggregate_type="batch", aggregate_id=uuid4(), partition_key="p"
        )
    )
    (msg,) = client.queue.drain()
    assert (msg.seq, msg.type) == (None, "telemetry.tick")


async def test_without_a_seq_source_the_seq_stays_empty() -> None:
    hub, bus = Hub(), InMemoryEventBus()
    register_realtime(bus, RealtimeEvents(hub))
    client = hub.connect()
    await bus.publish(alert_event())
    assert client.queue.drain()[0].seq is None
