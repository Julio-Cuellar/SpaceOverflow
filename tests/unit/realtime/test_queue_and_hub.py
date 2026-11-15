"""Cola por cliente con presión inversa (500 mensajes) y reparto por topics."""

from __future__ import annotations

import asyncio

from spaceapp.modules.realtime.application.hub import ClientQueue, Hub
from spaceapp.modules.realtime.domain.messages import WsMessage


def tick(zone: str = "z", metric: str = "co2", value: float = 1.0) -> WsMessage:
    return WsMessage(
        None,
        "telemetry",
        "telemetry.tick",
        "t",
        {"zone_id": zone, "metric": metric, "value": value},
    )


def alert(seq: int) -> WsMessage:
    return WsMessage(seq, "alerts", "alert.raised", "t", {"n": seq})


def test_a_new_tick_replaces_the_pending_one_of_the_same_zone_and_metric() -> None:
    q = ClientQueue(max_pending=500)
    q.push(tick(value=1.0))
    q.push(tick(value=2.0))
    q.push(tick(metric="o2", value=3.0))
    drained = q.drain()
    assert [m.data["value"] for m in drained] == [2.0, 3.0]


def test_when_full_ticks_are_dropped_before_alerts() -> None:
    q = ClientQueue(max_pending=5)
    for i in range(5):
        q.push(tick(zone=f"z{i}"))
    q.push(alert(1))
    q.push(alert(2))
    drained = q.drain()
    assert len(drained) == 5
    assert [m.seq for m in drained if m.type == "alert.raised"] == [1, 2]
    assert q.dropped == 2


def test_alerts_are_never_dropped_even_over_the_limit() -> None:
    q = ClientQueue(max_pending=3)
    for i in range(10):
        q.push(alert(i))
    assert len(q.drain()) == 10
    assert q.dropped == 0


async def test_get_waits_for_a_message_and_returns_everything_pending() -> None:
    q = ClientQueue(max_pending=5)
    waiter = asyncio.create_task(q.get())
    await asyncio.sleep(0)
    assert not waiter.done()
    q.push(alert(1))
    q.push(alert(2))
    assert [m.seq for m in await asyncio.wait_for(waiter, 1)] == [1, 2]


async def test_the_hub_delivers_only_the_topics_each_client_chose() -> None:
    hub = Hub()
    all_topics = hub.connect()
    only_alerts = hub.connect()
    only_alerts.unsubscribe(["telemetry", "assistant"])
    await hub.broadcast(tick())
    await hub.broadcast(alert(1))
    assert [m.type for m in all_topics.queue.drain()] == ["telemetry.tick", "alert.raised"]
    assert [m.type for m in only_alerts.queue.drain()] == ["alert.raised"]


async def test_subscribe_adds_topics_and_disconnect_stops_delivery() -> None:
    hub = Hub()
    c = hub.connect()
    c.unsubscribe(["telemetry"])
    await hub.broadcast(tick())
    assert c.queue.drain() == []
    c.subscribe(["telemetry"])
    await hub.broadcast(tick())
    assert len(c.queue.drain()) == 1
    hub.disconnect(c)
    await hub.broadcast(tick())
    assert c.queue.drain() == []
    assert hub.client_count == 0


def test_unknown_topics_are_rejected() -> None:
    c = Hub().connect()
    try:
        c.subscribe(["nope"])
    except ValueError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("debía rechazar el topic")
