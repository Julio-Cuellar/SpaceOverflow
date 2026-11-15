"""Plan from Ground end to end (F11): draft → link → ship → Missions → acknowledgement."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from spaceapp.modules.engagement.adapters.inbound.events import register_engagement
from spaceapp.modules.engagement.facade import GroundTemplateQuery
from spaceapp.modules.groundlink.adapters.inbound.events import register_groundlink
from spaceapp.modules.groundlink.adapters.inbound.rest import build_router
from spaceapp.modules.groundlink.adapters.outbound.sql import SqlGroundlinkRepository
from spaceapp.modules.groundlink.application.ground import GroundControl, Ok, Refused, ship_template
from spaceapp.modules.groundlink.application.receiver import PlanReceiver
from spaceapp.modules.groundlink.domain.plans import ShipTemplate, plan_hash
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.outbox import OutboxRelay
from tests.integration.engagement.test_tasks import NOW
from tests.integration.engagement.test_tasks import World as EngagementWorld

pytestmark = pytest.mark.integration


class World(EngagementWorld):
    def __init__(self, sf: Any) -> None:
        super().__init__(sf)
        self.scheduled: list[Callable[[], Awaitable[None]]] = []
        self.receiver = PlanReceiver(sf, SqlGroundlinkRepository, uuid4(), clock=lambda: NOW)
        self.ground = GroundControl(
            sf,
            SqlGroundlinkRepository,
            self.receiver,
            self._ship_templates,
            lambda _delay, job: self.scheduled.append(job),
            uuid4(),
            clock=lambda: NOW,
        )
        registry = SubscriptionRegistry()
        register_engagement(registry, self.service)
        register_groundlink(registry, self.receiver, self.ground)
        self.relay = OutboxRelay(sf, registry)

    async def _ship_templates(self) -> list[ShipTemplate]:
        rows = await GroundTemplateQuery(self.sf).list()
        return [
            ship_template(r.template_id, r.title, r.kind, r.task_status, r.blocked_reason)
            for r in rows
            if r.active
        ]

    async def link_delivers(self) -> None:
        """Lets the link delay elapse: what was scheduled is delivered and the ship processes its events."""
        jobs, self.scheduled = self.scheduled, []
        for job in jobs:
            await job()
        await self.drain()

    async def stage(self) -> str:
        view = await self.ground.view()
        assert view.published is not None
        return view.published.status

    async def ground_tasks(self) -> list[Any]:
        return [t for t in await self.today() if t.origin == "GROUND"]


@pytest.fixture
def world(session_factory: Any) -> World:
    return World(session_factory)


async def test_a_published_plan_travels_is_applied_and_confirmed(world: World) -> None:
    assert await world.ground.save_template(title="Ground exercise", kind="HEALTH") == Ok(1)
    view = await world.ground.view()
    assert view.draft_version == 1 and [t.status for t in view.draft or []] == ["PENDING"]

    assert await world.ground.publish() == Ok(1)
    assert await world.stage() == "IN_TRANSIT"
    await world.link_delivers()
    assert await world.stage() == "CONFIRMED"

    [task] = await world.ground_tasks()
    assert task.title == "Ground exercise"
    view = await world.ground.view()
    assert view.applied_version == 1 and view.draft is None
    assert [(t.title, t.status) for t in view.templates] == [("Ground exercise", "APPLIED")]


async def test_with_the_link_down_the_plan_waits_and_arrives_when_it_returns(world: World) -> None:
    await world.ground.set_link(False)
    await world.ground.save_template(title="Hydration", kind="HEALTH")
    await world.ground.publish()
    assert await world.stage() == "QUEUED" and world.scheduled == []
    assert await world.ground_tasks() == []

    await world.ground.set_link(True)
    assert await world.stage() == "IN_TRANSIT"
    await world.link_delivers()
    assert await world.stage() == "CONFIRMED"
    assert [t.title for t in await world.ground_tasks()] == ["Hydration"]


async def test_a_cut_while_in_flight_returns_the_plan_to_the_queue(world: World) -> None:
    await world.ground.save_template(title="Sleep", kind="HEALTH")
    await world.ground.publish()
    await world.ground.set_link(False)
    await world.link_delivers()
    assert await world.stage() == "QUEUED"
    await world.ground.set_link(True)
    await world.link_delivers()
    assert await world.stage() == "CONFIRMED"


async def test_the_confirmation_waits_for_the_link_too(world: World) -> None:
    await world.ground.save_template(title="Sleep", kind="HEALTH")
    await world.ground.publish()
    jobs, world.scheduled = world.scheduled, []
    for job in jobs:
        await job()  # it reaches the ship
    await world.ground.set_link(False)  # the link drops before the acknowledgement goes up
    await world.drain()
    assert await world.stage() == "APPLIED"
    await world.ground.set_link(True)
    assert await world.stage() == "CONFIRMED"


async def test_only_one_plan_in_flight_and_nothing_empty_is_published(world: World) -> None:
    empty = await world.ground.publish()
    assert isinstance(empty, Refused) and empty.code == "NOTHING_TO_PUBLISH"
    await world.ground.save_template(title="A", kind="HEALTH")
    await world.ground.publish()
    await world.ground.save_template(title="B", kind="SHIP")
    busy = await world.ground.publish()
    assert isinstance(busy, Refused) and busy.code == "PLAN_IN_FLIGHT"


async def test_cancelling_keeps_what_the_crew_completed_and_shows_blocks(world: World) -> None:
    await world.ground.save_template(title="Exercise", kind="HEALTH")
    await world.ground.save_template(title="Filters", kind="SHIP", zone_code="lab")
    await world.ground.publish()
    await world.link_delivers()
    exercise, filters = sorted(await world.ground_tasks(), key=lambda t: t.title)
    await world.service.complete(exercise.id, True)
    await world.service.block(filters.id, "No spare part")

    shown = {t.title: t for t in (await world.ground.view()).templates}
    assert shown["Exercise"].status == "COMPLETED"
    assert (shown["Filters"].status, shown["Filters"].blocked_reason) == (
        "BLOCKED",
        "No spare part",
    )

    assert exercise.template_id is not None
    await world.ground.cancel_template(exercise.template_id)
    draft = {t.title: t for t in (await world.ground.view()).draft or []}
    assert draft["Exercise"].cancelled and not draft["Filters"].cancelled
    await world.ground.publish()
    await world.link_delivers()
    assert await world.stage() == "CONFIRMED"
    done = await world.tasks.get(exercise.id)
    assert done is not None and done.status == "COMPLETED", "what was completed is not lost"
    assert [t.title for t in (await world.ground.view()).templates] == ["Filters"]


async def test_an_invalid_item_is_rejected_alone_and_the_plan_is_still_confirmed(
    world: World,
) -> None:
    await world.ground.save_template(title="Good", kind="HEALTH")
    await world.ground.save_template(title="Outside", kind="SHIP", zone_code="mars")
    await world.ground.publish()
    await world.link_delivers()
    assert await world.stage() == "CONFIRMED"
    assert [t.title for t in await world.ground_tasks()] == ["Good"]
    async with world.sf() as s:
        rejected = (
            await s.execute(text("SELECT rejected FROM groundlink.inbound_plan"))
        ).scalar_one()
    rejected = rejected if isinstance(rejected, list) else json.loads(rejected)
    assert rejected == [{"title": "Outside", "reason": "nonexistent zone 'mars'"}]


async def test_r9_rejects_a_corrupt_plan_whole_and_ignores_repeats(world: World) -> None:
    app = FastAPI()
    app.include_router(build_router(lambda: (world.receiver, world.ground)))
    items = [{"change": "NEW", "kind": "HEALTH", "title": "From R9"}]
    good = {
        "batch_id": str(uuid4()),
        "plan_version": 5,
        "items": items,
        "hash": plan_hash(5, items),
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        corrupt = await client.post(
            "/api/v1/groundlink/inbound/plans", json={**good, "hash": "0" * 64}
        )
        assert corrupt.status_code == 422 and "integrity" in corrupt.json()["reason"]
        first = await client.post("/api/v1/groundlink/inbound/plans", json=good)
        again = await client.post("/api/v1/groundlink/inbound/plans", json=good)
        older = {**good, "batch_id": str(uuid4()), "plan_version": 4, "hash": plan_hash(4, items)}
        old = await client.post("/api/v1/groundlink/inbound/plans", json=older)
        assert (first.status_code, again.json(), old.json()) == (
            202,
            {"status": "ignored"},
            {"status": "ignored"},
        )
        bad_item = [{"change": "NEW", "kind": "HEALTH", "title": "x", "extra": 1}]
        malformed = await client.post(
            "/api/v1/groundlink/inbound/plans",
            json={
                **good,
                "batch_id": str(uuid4()),
                "plan_version": 6,
                "items": bad_item,
                "hash": plan_hash(6, bad_item),
            },
        )
        assert malformed.status_code == 422
        link = await client.put("/api/v1/groundlink/link", json={"state": "DOWN", "delay_s": 5})
        assert link.json() == {"state": "DOWN", "delay_s": 5.0}
    await world.drain()
    assert [t.title for t in await world.ground_tasks()] == ["From R9"]
