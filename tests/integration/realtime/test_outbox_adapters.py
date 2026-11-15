"""Gateway sobre el outbox real: el seq es el id del outbox y `resume` lo reenvía."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.monitoring.contracts import AlertRaised, AlertResolved
from spaceapp.modules.realtime.adapters.inbound.events import RealtimeEvents, register_realtime
from spaceapp.modules.realtime.adapters.outbound.sql import SqlOutboxReplay, seq_of
from spaceapp.modules.realtime.application.hub import Hub
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork

pytestmark = pytest.mark.integration


def raised() -> EventEnvelope:
    aid = uuid4()
    return EventEnvelope.from_payload(
        AlertRaised(alert_id=aid, zone_id=None, rule_key="r", severity="atencion", evidence={}),
        aggregate_type="alert",
        aggregate_id=aid,
        partition_key="p",
    )


def resolved() -> EventEnvelope:
    from datetime import UTC, datetime

    aid = uuid4()
    return EventEnvelope.from_payload(
        AlertResolved(alert_id=aid, resolved_at=datetime.now(UTC), duration_s=3),
        aggregate_type="alert",
        aggregate_id=aid,
        partition_key="p",
    )


async def publish(sf, *events):  # type: ignore[no-untyped-def]
    async with UnitOfWork(sf) as uow:
        for e in events:
            await uow.publish(e)


async def test_the_relay_delivers_to_the_hub_with_the_outbox_id_as_seq(session_factory) -> None:  # type: ignore[no-untyped-def]
    hub, registry = Hub(), SubscriptionRegistry()
    register_realtime(registry, RealtimeEvents(hub, seq_of))
    client = hub.connect()
    first, second = raised(), resolved()
    await publish(session_factory, first, second)
    await OutboxRelay(session_factory, registry).run_once()
    got = client.queue.drain()
    assert [m.type for m in got] == ["alert.raised", "alert.resolved"]
    async with session_factory() as s:
        ids = [
            r[0] for r in await s.execute(text("SELECT id FROM platform.outbox_event ORDER BY id"))
        ]
    assert [m.seq for m in got] == ids


async def test_resume_returns_only_delivered_events_after_the_given_id(session_factory) -> None:  # type: ignore[no-untyped-def]
    hub, registry = Hub(), SubscriptionRegistry()
    register_realtime(registry, RealtimeEvents(hub, seq_of))
    await publish(session_factory, raised(), raised(), raised())
    await OutboxRelay(session_factory, registry).run_once()
    await publish(session_factory, raised())  # este sigue pendiente: no se reenvía
    replay = SqlOutboxReplay(session_factory)
    everything = await replay.after(0, 100)
    assert [m.seq for m in everything] == [1, 2, 3]
    assert [m.seq for m in await replay.after(1, 100)] == [2, 3]
    assert [m.seq for m in await replay.after(0, 2)] == [1, 2]
    assert await replay.after(3, 100) == []


async def test_resume_ignores_events_older_than_the_retention_window(session_factory) -> None:  # type: ignore[no-untyped-def]
    registry = SubscriptionRegistry()
    register_realtime(registry, RealtimeEvents(Hub(), seq_of))
    await publish(session_factory, raised(), raised())
    await OutboxRelay(session_factory, registry).run_once()
    async with session_factory() as s, s.begin():
        await s.execute(
            text(
                "UPDATE platform.outbox_event SET occurred_at = now() - interval '25 hours' WHERE id = 1"
            )
        )
    assert [m.seq for m in await SqlOutboxReplay(session_factory).after(0, 100)] == [2]


async def test_resume_skips_readings_because_ticks_have_no_seq(session_factory) -> None:  # type: ignore[no-untyped-def]
    async with session_factory() as s, s.begin():
        await s.execute(
            text(
                "INSERT INTO platform.outbox_event (event_id, type, aggregate_type, aggregate_id, "
                "partition_key, payload, status) VALUES (:e, 'telemetry.readings_recorded', 'b', :a, "
                "'p', CAST('{\"latest\": [], \"ts_to\": \"x\"}' AS jsonb), 'done')"
            ),
            {"e": uuid4(), "a": uuid4()},
        )
    assert await SqlOutboxReplay(session_factory).after(0, 100) == []
