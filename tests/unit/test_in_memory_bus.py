from typing import ClassVar
from uuid import uuid4

import pytest

from spaceapp.platform.bus import HandlerContext, InMemoryEventBus
from spaceapp.platform.events import EventEnvelope, EventPayload


class Pinged(EventPayload):
    event_type: ClassVar[str] = "demo.pinged"
    n: int


class Ponged(EventPayload):
    event_type: ClassVar[str] = "demo.ponged"
    n: int


def ev(payload: EventPayload) -> EventEnvelope:
    return EventEnvelope.from_payload(
        payload, aggregate_type="demo", aggregate_id=uuid4(), partition_key="k"
    )


async def test_subscriber_receives_the_event():
    bus, seen = InMemoryEventBus(), []

    async def handler(e: EventEnvelope, ctx: HandlerContext) -> None:
        seen.append(e.payload_as(Pinged).n)

    bus.subscribe("demo.pinged", "c1", handler)
    await bus.publish(ev(Pinged(n=5)))
    assert seen == [5]


async def test_event_without_subscribers_is_fine():
    await InMemoryEventBus().publish(ev(Pinged(n=1)))


async def test_each_consumer_gets_its_own_copy():
    bus, seen = InMemoryEventBus(), []

    def make(name: str):
        async def handler(e: EventEnvelope, ctx: HandlerContext) -> None:
            seen.append(name)

        return handler

    bus.subscribe("demo.pinged", "a", make("a"))
    bus.subscribe("demo.pinged", "b", make("b"))
    await bus.publish(ev(Pinged(n=1)))
    assert sorted(seen) == ["a", "b"]


async def test_the_same_event_is_not_processed_twice_by_a_consumer():
    bus, calls = InMemoryEventBus(), []

    async def handler(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls.append(e.event_id)

    bus.subscribe("demo.pinged", "c1", handler)
    e = ev(Pinged(n=1))
    await bus.publish(e)
    await bus.publish(e)
    assert len(calls) == 1


async def test_events_published_by_a_handler_are_delivered_after_it_finishes():
    bus, order = InMemoryEventBus(), []

    async def on_ping(e: EventEnvelope, ctx: HandlerContext) -> None:
        order.append("ping:start")
        await ctx.publish(ev(Ponged(n=1)))
        order.append("ping:end")

    async def on_pong(e: EventEnvelope, ctx: HandlerContext) -> None:
        order.append("pong")

    bus.subscribe("demo.pinged", "p", on_ping)
    bus.subscribe("demo.ponged", "q", on_pong)
    await bus.publish(ev(Pinged(n=1)))
    assert order == ["ping:start", "ping:end", "pong"]


async def test_a_failing_handler_does_not_stop_the_others_and_the_error_surfaces():
    bus, ok = InMemoryEventBus(), []

    async def bad(e: EventEnvelope, ctx: HandlerContext) -> None:
        raise RuntimeError("boom")

    async def good(e: EventEnvelope, ctx: HandlerContext) -> None:
        ok.append(True)

    bus.subscribe("demo.pinged", "bad", bad)
    bus.subscribe("demo.pinged", "good", good)
    with pytest.raises(RuntimeError, match="boom"):
        await bus.publish(ev(Pinged(n=1)))
    assert ok == [True]
    assert bus.failures[0][0] == "bad"


async def test_in_memory_context_has_no_database_session():
    bus, sessions = InMemoryEventBus(), []

    async def handler(e: EventEnvelope, ctx: HandlerContext) -> None:
        sessions.append(ctx.session)

    bus.subscribe("demo.pinged", "c", handler)
    await bus.publish(ev(Pinged(n=1)))
    assert sessions == [None]


async def test_a_consumer_cannot_subscribe_twice_to_the_same_event():
    bus = InMemoryEventBus()

    async def handler(e: EventEnvelope, ctx: HandlerContext) -> None:
        return None

    bus.subscribe("demo.pinged", "c1", handler)
    with pytest.raises(ValueError, match="is already subscribed"):
        bus.subscribe("demo.pinged", "c1", handler)
