import asyncio
from datetime import timedelta
from typing import ClassVar
from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.platform.bus import HandlerContext, SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork, backoff_seconds

pytestmark = pytest.mark.integration


class Pinged(EventPayload):
    event_type: ClassVar[str] = "demo.pinged"
    n: int


class Ponged(EventPayload):
    event_type: ClassVar[str] = "demo.ponged"
    n: int


def ev(n: int = 1, payload: type[EventPayload] = Pinged) -> EventEnvelope:
    return EventEnvelope.from_payload(
        payload(n=n), aggregate_type="demo", aggregate_id=uuid4(), partition_key="k"
    )


async def publish(sf, *events: EventEnvelope) -> None:  # type: ignore[no-untyped-def]
    async with UnitOfWork(sf) as uow:
        for e in events:
            await uow.publish(e)


async def rows(sf, sql: str = "SELECT * FROM platform.outbox_event ORDER BY id"):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return [dict(r) for r in (await s.execute(text(sql))).mappings().all()]


async def make_due(sf) -> None:  # type: ignore[no-untyped-def]
    async with sf() as s, s.begin():
        await s.execute(text("UPDATE platform.outbox_event SET next_attempt_at = now()"))


def relay(sf, registry, **kw):  # type: ignore[no-untyped-def]
    return OutboxRelay(sf, registry, **kw)


# ---- entrega básica -------------------------------------------------------------------


async def test_delivers_a_pending_event_and_marks_it_done(session_factory):
    reg, seen = SubscriptionRegistry(), []

    async def h(e: EventEnvelope, ctx: HandlerContext) -> None:
        seen.append(e.payload_as(Pinged).n)
        assert ctx.session is not None

    reg.subscribe("demo.pinged", "c1", h)
    await publish(session_factory, ev(4))
    assert await relay(session_factory, reg).run_once() == 1
    assert seen == [4]
    assert (await rows(session_factory))[0]["status"] == "done"
    inbox = await rows(session_factory, "SELECT consumer FROM platform.inbox_processed")
    assert inbox == [{"consumer": "c1"}]


async def test_an_event_without_subscribers_is_marked_done(session_factory):
    await publish(session_factory, ev())
    await relay(session_factory, SubscriptionRegistry()).run_once()
    assert (await rows(session_factory))[0]["status"] == "done"


async def test_events_are_delivered_in_order(session_factory):
    reg, seen = SubscriptionRegistry(), []

    async def h(e: EventEnvelope, ctx: HandlerContext) -> None:
        seen.append(e.payload_as(Pinged).n)

    reg.subscribe("demo.pinged", "c1", h)
    await publish(session_factory, *[ev(n) for n in range(1, 6)])
    await relay(session_factory, reg).run_once()
    assert seen == [1, 2, 3, 4, 5]


async def test_a_run_handles_at_most_batch_size_events(session_factory):
    await publish(session_factory, *[ev(n) for n in range(3)])
    r = relay(session_factory, SubscriptionRegistry(), batch_size=2)
    assert await r.run_once() == 2
    assert await r.run_once() == 1
    assert await r.run_once() == 0


# ---- fallos, reintentos y eventos muertos -----------------------------------------------


def test_backoff_doubles_from_one_second_up_to_sixty():
    assert [backoff_seconds(a) for a in range(1, 9)] == [1, 2, 4, 8, 16, 32, 60, 60]


async def test_a_failing_handler_leaves_the_event_pending_with_backoff(session_factory):
    reg = SubscriptionRegistry()

    async def bad(e: EventEnvelope, ctx: HandlerContext) -> None:
        raise RuntimeError("boom")

    reg.subscribe("demo.pinged", "bad", bad)
    await publish(session_factory, ev())
    await relay(session_factory, reg).run_once()
    row = (await rows(session_factory))[0]
    assert row["status"] == "pending" and row["attempts"] == 1
    assert "bad" in row["last_error"] and "boom" in row["last_error"]
    async with session_factory() as s:
        wait = (
            await s.execute(
                text(
                    "SELECT extract(epoch FROM next_attempt_at - now()) FROM platform.outbox_event"
                )
            )
        ).scalar_one()
    assert 0 < float(wait) <= 1.01


async def test_a_failed_event_is_not_retried_before_its_time(session_factory):
    reg, calls = SubscriptionRegistry(), []

    async def bad(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls.append(1)
        raise RuntimeError("boom")

    reg.subscribe("demo.pinged", "bad", bad)
    await publish(session_factory, ev())
    r = relay(session_factory, reg)
    await r.run_once()
    await make_due(session_factory)  # simula que pasó el tiempo
    await r.run_once()
    assert len(calls) == 2
    assert (await rows(session_factory))[0]["attempts"] == 2
    assert await r.run_once() == 0  # el segundo backoff (2 s) todavía no venció
    assert len(calls) == 2


async def test_a_handler_that_recovers_completes_the_event(session_factory):
    reg, state = SubscriptionRegistry(), {"fail": True}

    async def flaky(e: EventEnvelope, ctx: HandlerContext) -> None:
        if state["fail"]:
            raise RuntimeError("todavía no")

    reg.subscribe("demo.pinged", "flaky", flaky)
    await publish(session_factory, ev())
    r = relay(session_factory, reg)
    await r.run_once()
    state["fail"] = False
    await make_due(session_factory)
    await r.run_once()
    row = (await rows(session_factory))[0]
    assert row["status"] == "done" and row["last_error"] is None


async def test_after_max_attempts_the_event_is_dead_and_left_alone(session_factory):
    reg, calls = SubscriptionRegistry(), []

    async def bad(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls.append(1)
        raise RuntimeError("siempre falla")

    reg.subscribe("demo.pinged", "bad", bad)
    await publish(session_factory, ev())
    r = relay(session_factory, reg, max_attempts=3)
    for _ in range(3):
        await make_due(session_factory)
        await r.run_once()
    row = (await rows(session_factory))[0]
    assert row["status"] == "dead" and row["attempts"] == 3
    assert "siempre falla" in row["last_error"]
    await make_due(session_factory)
    assert await r.run_once() == 0
    assert len(calls) == 3


async def test_default_max_attempts_is_eight(session_factory):
    assert relay(session_factory, SubscriptionRegistry()).max_attempts == 8


# ---- inbox: idempotencia y aislamiento --------------------------------------------------


async def test_a_failing_consumer_does_not_block_the_others_nor_rerun_them(session_factory):
    reg, calls = SubscriptionRegistry(), {"good": 0, "bad": 0}

    async def good(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls["good"] += 1

    async def bad(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls["bad"] += 1
        raise RuntimeError("boom")

    reg.subscribe("demo.pinged", "good", good)
    reg.subscribe("demo.pinged", "bad", bad)
    await publish(session_factory, ev())
    r = relay(session_factory, reg)
    await r.run_once()
    await make_due(session_factory)
    await r.run_once()
    assert calls == {"good": 1, "bad": 2}  # good no se repite: el inbox lo omite


async def test_an_event_already_in_the_inbox_is_not_handled_again(session_factory):
    reg, calls = SubscriptionRegistry(), []

    async def h(e: EventEnvelope, ctx: HandlerContext) -> None:
        calls.append(1)

    reg.subscribe("demo.pinged", "c1", h)
    e = ev()
    await publish(session_factory, e)
    async with session_factory() as s, s.begin():
        await s.execute(
            text("INSERT INTO platform.inbox_processed (consumer, event_id) VALUES ('c1', :i)"),
            {"i": e.event_id},
        )
    await relay(session_factory, reg).run_once()
    assert calls == []
    assert (await rows(session_factory))[0]["status"] == "done"


async def test_handler_writes_and_inbox_mark_commit_together(session_factory):
    reg = SubscriptionRegistry()

    async def writes(e: EventEnvelope, ctx: HandlerContext) -> None:
        assert ctx.session is not None
        await ctx.session.execute(text("INSERT INTO public.demo_state VALUES ('hecho')"))

    reg.subscribe("demo.pinged", "w", writes)
    await publish(session_factory, ev())
    await relay(session_factory, reg).run_once()
    assert len(await rows(session_factory, "SELECT * FROM public.demo_state")) == 1
    assert len(await rows(session_factory, "SELECT * FROM platform.inbox_processed")) == 1


async def test_a_failure_after_writing_rolls_back_the_handler_and_its_inbox_mark(session_factory):
    reg = SubscriptionRegistry()

    async def writes_then_fails(e: EventEnvelope, ctx: HandlerContext) -> None:
        assert ctx.session is not None
        await ctx.session.execute(text("INSERT INTO public.demo_state VALUES ('a medias')"))
        raise RuntimeError("boom")

    reg.subscribe("demo.pinged", "w", writes_then_fails)
    await publish(session_factory, ev())
    await relay(session_factory, reg).run_once()
    assert await rows(session_factory, "SELECT * FROM public.demo_state") == []
    assert await rows(session_factory, "SELECT * FROM platform.inbox_processed") == []


async def test_a_handler_can_publish_a_follow_up_event_in_its_own_transaction(session_factory):
    reg, seen = SubscriptionRegistry(), []

    async def on_ping(e: EventEnvelope, ctx: HandlerContext) -> None:
        await ctx.publish(ev(e.payload_as(Pinged).n + 1, Ponged))

    async def on_pong(e: EventEnvelope, ctx: HandlerContext) -> None:
        seen.append(e.payload_as(Ponged).n)

    reg.subscribe("demo.pinged", "p", on_ping)
    reg.subscribe("demo.ponged", "q", on_pong)
    await publish(session_factory, ev(1))
    r = relay(session_factory, reg)
    await r.run_once()
    pending = await rows(
        session_factory, "SELECT type FROM platform.outbox_event WHERE status='pending'"
    )
    assert pending == [{"type": "demo.ponged"}]
    await r.run_once()
    assert seen == [2]


async def test_a_follow_up_event_is_discarded_if_the_handler_fails(session_factory):
    reg = SubscriptionRegistry()

    async def publishes_then_fails(e: EventEnvelope, ctx: HandlerContext) -> None:
        await ctx.publish(ev(9, Ponged))
        raise RuntimeError("boom")

    reg.subscribe("demo.pinged", "p", publishes_then_fails)
    await publish(session_factory, ev())
    await relay(session_factory, reg).run_once()
    types = await rows(session_factory, "SELECT type FROM platform.outbox_event ORDER BY id")
    assert types == [{"type": "demo.pinged"}]


# ---- concurrencia y modo continuo -------------------------------------------------------


async def test_two_relays_never_handle_the_same_event_twice(session_factory):
    reg, handled = SubscriptionRegistry(), []

    async def slow(e: EventEnvelope, ctx: HandlerContext) -> None:
        await asyncio.sleep(0.05)
        handled.append(e.payload_as(Pinged).n)

    reg.subscribe("demo.pinged", "c", slow)
    await publish(session_factory, *[ev(n) for n in range(8)])
    a, b = relay(session_factory, reg, batch_size=4), relay(session_factory, reg, batch_size=4)
    await asyncio.gather(a.run_once(), b.run_once())
    await a.run_once()
    assert sorted(handled) == list(range(8))


async def _run_in_background(r: OutboxRelay):  # type: ignore[no-untyped-def]
    stop = asyncio.Event()
    task = asyncio.create_task(r.run_forever(stop))
    return stop, task


async def test_run_forever_wakes_up_on_notify_without_waiting_for_the_poll(
    session_factory, listen_dsn
):
    reg, got = SubscriptionRegistry(), asyncio.Event()

    async def h(e: EventEnvelope, ctx: HandlerContext) -> None:
        got.set()

    reg.subscribe("demo.pinged", "c", h)
    r = relay(session_factory, reg, poll_interval=30, listen_dsn=listen_dsn)
    stop, task = await _run_in_background(r)
    try:
        await asyncio.sleep(0.3)  # deja que el relay empiece a escuchar
        await publish(session_factory, ev())
        await asyncio.wait_for(got.wait(), timeout=3)
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=3)


async def test_run_forever_also_works_by_polling_only(session_factory):
    reg, got = SubscriptionRegistry(), asyncio.Event()

    async def h(e: EventEnvelope, ctx: HandlerContext) -> None:
        got.set()

    reg.subscribe("demo.pinged", "c", h)
    stop, task = await _run_in_background(relay(session_factory, reg, poll_interval=0.05))
    try:
        await publish(session_factory, ev())
        await asyncio.wait_for(got.wait(), timeout=3)
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=3)


async def test_run_forever_stops_when_asked(session_factory):
    stop, task = await _run_in_background(
        relay(session_factory, SubscriptionRegistry(), poll_interval=0.05)
    )
    stop.set()
    await asyncio.wait_for(task, timeout=3)
    assert task.done() and task.exception() is None


async def test_an_old_pending_event_has_a_measurable_lag(session_factory):
    await publish(session_factory, ev())
    async with session_factory() as s, s.begin():
        await s.execute(
            text("UPDATE platform.outbox_event SET occurred_at = :t"),
            {"t": (await s.execute(text("SELECT now()"))).scalar_one() - timedelta(seconds=30)},
        )
    from spaceapp.platform.outbox import outbox_stats

    async with session_factory() as s:
        stats = await outbox_stats(s)
    assert stats.pending == 1 and stats.dead == 0
    assert stats.oldest_pending_age_s is not None and stats.oldest_pending_age_s >= 29
