import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from spaceapp.main import create_app
from spaceapp.platform.config import Settings
from tests.integration.test_relay import ev, publish

pytestmark = pytest.mark.integration


def client(app) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_ready_reports_pending_and_dead_events(session_factory):
    await publish(session_factory, ev(1), ev(2))
    async with session_factory() as s, s.begin():
        await s.execute(
            text("UPDATE platform.outbox_event SET status='dead', last_error='x' WHERE id = 1")
        )
    app = create_app(Settings(), session_factory=session_factory)
    async with client(app) as c:
        r = await c.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["outbox"]["pending"] == 1 and body["outbox"]["dead"] == 1
    assert body["outbox"]["oldest_pending_age_s"] >= 0


async def test_ready_with_an_empty_outbox_has_no_lag(session_factory):
    app = create_app(Settings(), session_factory=session_factory)
    async with client(app) as c:
        body = (await c.get("/ready")).json()
    assert body["outbox"] == {"pending": 0, "dead": 0, "oldest_pending_age_s": None}


async def test_ready_answers_503_when_the_database_is_unreachable():
    bad = create_async_engine("postgresql+asyncpg://x:y@127.0.0.1:1/none")
    app = create_app(Settings(), session_factory=async_sessionmaker(bad))
    async with client(app) as c:
        r = await c.get("/ready")
    await bad.dispose()
    assert r.status_code == 503
    assert r.json()["status"] == "unavailable"
