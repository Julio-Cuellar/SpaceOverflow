import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork


def test_a_unit_of_work_that_was_not_entered_has_no_session():
    uow = UnitOfWork(
        async_sessionmaker(create_async_engine("postgresql+asyncpg://x:y@127.0.0.1:1/n"))
    )
    with pytest.raises(RuntimeError, match="is not active"):
        _ = uow.session


async def test_the_relay_survives_an_unreachable_database_and_still_stops():
    engine = create_async_engine("postgresql+asyncpg://x:y@127.0.0.1:1/none")
    relay = OutboxRelay(async_sessionmaker(engine), SubscriptionRegistry(), poll_interval=0.05)
    stop = asyncio.Event()
    task = asyncio.create_task(relay.run_forever(stop))
    await asyncio.sleep(0.3)  # several failed cycles
    assert not task.done()
    stop.set()
    await asyncio.wait_for(task, timeout=3)
    await engine.dispose()
