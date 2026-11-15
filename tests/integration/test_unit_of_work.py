import asyncio
from typing import ClassVar
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text

from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.outbox import UnitOfWork

pytestmark = pytest.mark.integration


class Pinged(EventPayload):
    event_type: ClassVar[str] = "demo.pinged"
    n: int


def ev(n: int = 1) -> EventEnvelope:
    return EventEnvelope.from_payload(
        Pinged(n=n), aggregate_type="demo", aggregate_id=uuid4(), partition_key="habitat:h1"
    )


async def count(sf, table: str) -> int:  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (await s.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def test_state_and_event_are_committed_together(session_factory):
    e = ev(7)
    async with UnitOfWork(session_factory) as uow:
        await uow.session.execute(text("INSERT INTO public.demo_state VALUES ('hola')"))
        await uow.publish(e)
    assert await count(session_factory, "public.demo_state") == 1
    async with session_factory() as s:
        row = (
            (
                await s.execute(
                    text(
                        "SELECT type, status, attempts, payload->>'n' AS n, partition_key "
                        "FROM platform.outbox_event"
                    )
                )
            )
            .mappings()
            .one()
        )
    assert dict(row) == {
        "type": "demo.pinged",
        "status": "pending",
        "attempts": 0,
        "n": "7",
        "partition_key": "habitat:h1",
    }


async def test_if_the_use_case_fails_neither_state_nor_event_are_saved(session_factory):
    with pytest.raises(RuntimeError):
        async with UnitOfWork(session_factory) as uow:
            await uow.session.execute(text("INSERT INTO public.demo_state VALUES ('x')"))
            await uow.publish(ev())
            raise RuntimeError("falló el caso de uso")
    assert await count(session_factory, "public.demo_state") == 0
    assert await count(session_factory, "platform.outbox_event") == 0


async def test_publishing_the_same_event_twice_is_rejected(session_factory):
    e = ev()
    with pytest.raises(Exception, match=r"event_id|duplicate|unique"):
        async with UnitOfWork(session_factory) as uow:
            await uow.publish(e)
            await uow.publish(e)
    assert await count(session_factory, "platform.outbox_event") == 0


async def _listener(dsn: str):  # type: ignore[no-untyped-def]
    got: asyncio.Queue[str] = asyncio.Queue()
    conn = await asyncpg.connect(dsn)
    await conn.add_listener("outbox_new", lambda *a: got.put_nowait(a[3]))
    return conn, got


async def test_commit_sends_a_notify_to_wake_the_relay(session_factory, listen_dsn):
    conn, got = await _listener(listen_dsn)
    try:
        async with UnitOfWork(session_factory) as uow:
            await uow.publish(ev())
        assert await asyncio.wait_for(got.get(), timeout=2)
    finally:
        await conn.close()


async def test_rollback_sends_no_notify(session_factory, listen_dsn):
    conn, got = await _listener(listen_dsn)
    try:
        with pytest.raises(RuntimeError):
            async with UnitOfWork(session_factory) as uow:
                await uow.publish(ev())
                raise RuntimeError("rollback")
        await asyncio.sleep(0.3)
        assert got.empty()
    finally:
        await conn.close()
