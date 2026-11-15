"""Operación del outbox (F5, tarea 5.4): reencolar un evento muerto (R8) y limpiar los `done` viejos."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from spaceapp.main import create_app
from spaceapp.platform.bus import HandlerContext, SubscriptionRegistry
from spaceapp.platform.config import Settings
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import OutboxRelay, purge_done, replay_event
from spaceapp.platform.profiles import Profile
from tests.integration.test_relay import Pinged, ev, publish, rows

pytestmark = pytest.mark.integration


async def _kill(sf: Any) -> int:
    """Deja un evento en `dead` y devuelve su id."""
    await publish(sf, ev(1))
    async with sf() as s, s.begin():
        await s.execute(
            text("UPDATE platform.outbox_event SET status = 'dead', attempts = 8, last_error = 'x'")
        )
    return int((await rows(sf))[0]["id"])


async def test_a_dead_event_is_replayed_from_scratch_and_delivered(session_factory: Any) -> None:
    event_id = await _kill(session_factory)
    async with session_factory() as s, s.begin():
        assert await replay_event(s, event_id) == "replayed"
    row = (await rows(session_factory))[0]
    assert (row["status"], row["attempts"], row["last_error"]) == ("pending", 0, None)

    reg, seen = SubscriptionRegistry(), []

    async def h(e: EventEnvelope, _: HandlerContext) -> None:
        seen.append(e.payload_as(Pinged).n)

    reg.subscribe("demo.pinged", "demo.h", h)
    await OutboxRelay(session_factory, reg).run_once()
    assert seen == [1]


async def test_only_dead_events_can_be_replayed(session_factory: Any) -> None:
    await publish(session_factory, ev(1))
    pending_id = int((await rows(session_factory))[0]["id"])
    async with session_factory() as s, s.begin():
        assert await replay_event(s, pending_id) == "not_dead"
        assert await replay_event(s, 999_999) == "not_found"


async def test_done_events_older_than_the_retention_are_purged(session_factory: Any) -> None:
    await publish(session_factory, ev(1), ev(2), ev(3))
    async with session_factory() as s, s.begin():
        await s.execute(
            text(
                "UPDATE platform.outbox_event SET status = 'done', "
                "occurred_at = now() - interval '25 hours' WHERE id IN (1, 2)"
            )
        )
        await s.execute(text("UPDATE platform.outbox_event SET status = 'dead' WHERE id = 2"))
    async with session_factory() as s, s.begin():
        assert await purge_done(s, timedelta(hours=24)) == 1
    left = [(r["id"], r["status"]) for r in await rows(session_factory)]
    assert left == [(2, "dead"), (3, "pending")], "los muertos y los pendientes no se borran"


def test_the_replay_route_exists_only_in_development_profiles() -> None:
    def paths(profile: Profile) -> set[str]:
        return set(create_app(Settings(profile=profile)).openapi()["paths"])

    route = "/api/v1/admin/outbox/{event_id}:replay"
    assert route in paths(Profile.DEV1) and route in paths(Profile.DEV2)
    assert route not in paths(Profile.JURADO)


async def test_the_replay_route_answers_with_the_outcome(
    async_url: str, session_factory: Any
) -> None:
    event_id = await _kill(session_factory)
    settings = Settings(profile=Profile.DEV1, database_url=async_url)
    with TestClient(create_app(settings)) as client:
        assert client.post(f"/api/v1/admin/outbox/{event_id}:replay").json() == {
            "id": event_id,
            "status": "replayed",
        }
        assert client.post(f"/api/v1/admin/outbox/{event_id}:replay").status_code == 409
        assert client.post("/api/v1/admin/outbox/424242:replay").status_code == 404


async def test_outbox_stats_are_exposed_by_graphql_only_in_development(
    async_url: str, session_factory: Any
) -> None:
    await _kill(session_factory)
    query = {"query": "{ outboxStats { pending dead oldestPendingAgeS } }"}
    for profile, expected in (
        (Profile.DEV1, {"pending": 0, "dead": 1, "oldestPendingAgeS": None}),
        (Profile.JURADO, None),
    ):
        settings = Settings(profile=profile, database_url=async_url)
        with TestClient(create_app(settings)) as client:
            got = client.post("/graphql", json=query).json()
        assert got["data"]["outboxStats"] == expected, profile


async def test_the_running_relay_purges_old_done_events(session_factory: Any) -> None:
    await publish(session_factory, ev(1))
    async with session_factory() as s, s.begin():
        await s.execute(
            text(
                "UPDATE platform.outbox_event SET status = 'done', "
                "occurred_at = now() - interval '25 hours'"
            )
        )
    stop = asyncio.Event()
    task = asyncio.create_task(
        OutboxRelay(session_factory, SubscriptionRegistry(), poll_interval=0.01).run_forever(stop)
    )
    await asyncio.sleep(0.2)
    stop.set()
    await asyncio.wait_for(task, 5)
    assert await rows(session_factory) == []
