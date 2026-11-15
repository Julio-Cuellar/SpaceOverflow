"""Missions and tasks on real PostgreSQL: F10 acceptance criteria and plan application."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.engagement.adapters.inbound.events import register_engagement
from spaceapp.modules.engagement.adapters.outbound.json_data import load_system_templates
from spaceapp.modules.engagement.adapters.outbound.sql import SqlEngagementRepository
from spaceapp.modules.engagement.application.service import Done, EngagementService, Failed
from spaceapp.modules.engagement.facade import GroundTemplateQuery, TaskQuery
from spaceapp.modules.facility.contracts import IncidentOpened, IncidentResolved
from spaceapp.modules.groundlink.contracts import GroundPlanReceived, PlanChange
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.ids import zone_id
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
CREW = uuid4()
ZONES = {"eng", "eclss", "lab", "med", "bridge", "air", "store", "gym", "galley", "crew"}
TITLES = {"ventilate": "Ventilate the zone", "filter": "Replace the filter"}


class World:
    def __init__(self, sf: Any) -> None:
        self.sf = sf
        self.service = EngagementService(
            sf,
            SqlEngagementRepository,
            system_templates=load_system_templates(ROOT / "data" / "engagement" / "templates.json"),
            zone_codes=ZONES,
            zone_id_of=lambda code: zone_id("transit-ship", code),
            crew_member=CREW,
            habitat_id=uuid4(),
            action_title=TITLES.get,
            clock=lambda: NOW,
        )
        registry = SubscriptionRegistry()
        register_engagement(registry, self.service)
        self.relay = OutboxRelay(sf, registry)
        self.tasks = TaskQuery(sf)

    async def emit(self, payload: EventPayload, aggregate_id: UUID | None = None) -> None:
        async with UnitOfWork(self.sf) as uow:
            await uow.publish(
                EventEnvelope.from_payload(
                    payload,
                    aggregate_type="x",
                    aggregate_id=aggregate_id or uuid4(),
                    partition_key="p",
                )
            )
        await self.drain()

    async def drain(self) -> None:
        while await self.relay.run_once():
            pass

    async def today(self, **kw: Any) -> list[Any]:
        return await self.tasks.day(NOW.date(), **kw)

    async def events(self, event_type: str) -> list[dict[str, Any]]:
        async with self.sf() as s:
            rows = await s.execute(
                text("SELECT payload FROM platform.outbox_event WHERE type = :t ORDER BY id"),
                {"t": event_type},
            )
            return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

    async def plan(self, version: int, *changes: PlanChange) -> None:
        await self.emit(
            GroundPlanReceived(batch_id=uuid4(), plan_version=version, changes=list(changes))
        )


@pytest.fixture
def world(session_factory: Any) -> World:
    return World(session_factory)


# --- daily tasks ----------------------------------------------------------------------


async def test_each_system_template_gets_one_task_per_day(world: World) -> None:
    await world.service.ensure_day()
    await world.service.ensure_day()
    tasks = await world.today()
    assert len(tasks) == 7 and {t.origin for t in tasks} == {"SYSTEM"}
    assert {t.kind for t in tasks} == {"HEALTH", "SHIP"}
    assert len(await world.events("engagement.task_assigned")) == 7
    seals = next(t for t in tasks if t.zone_id == zone_id("transit-ship", "air"))
    assert seals.due_at == NOW.replace(hour=9)


# --- own tasks ----------------------------------------------------------------------


async def test_the_crew_creates_its_own_task_without_any_ground_link(world: World) -> None:
    got = await world.service.create("HEALTH", " Stretch the back ", None, None)
    assert isinstance(got, Done)
    task = await world.tasks.get(got.task_id)
    assert task is not None and (task.origin, task.title, task.status) == (
        "CREW",
        "Stretch the back",
        "PENDING",
    )
    [created] = await world.events("engagement.task_created")
    assert created["origin"] == "CREW"
    bad = await world.service.create("INCIDENT", "x", None, None)
    assert isinstance(bad, Failed) and bad.code == "INVALID_KIND"


async def test_crew_tasks_can_be_edited_and_deleted(world: World) -> None:
    got = await world.service.create("SHIP", "Clean", None, None)
    assert isinstance(got, Done)
    lab = zone_id("transit-ship", "lab")
    assert await world.service.update(
        got.task_id, title="Clean the lab", zone_id=lab, due_at=None
    ) == Done(got.task_id)
    task = await world.tasks.get(got.task_id)
    assert task is not None and (task.title, task.zone_id) == ("Clean the lab", lab)
    assert await world.service.delete(got.task_id) == Done(got.task_id)
    assert await world.tasks.get(got.task_id) is None


async def test_system_and_ground_tasks_reject_edit_and_delete_with_a_typed_error(
    world: World,
) -> None:
    await world.plan(1, PlanChange(change="NEW", kind="HEALTH", title="Ground exercise"))
    await world.service.ensure_day()
    for origin in ("GROUND", "SYSTEM"):
        task = (await world.today(kind="HEALTH"))[0] if origin == "SYSTEM" else None
        task = task or next(t for t in await world.today() if t.origin == "GROUND")
        edit = await world.service.update(task.id, title="x", zone_id=None, due_at=None)
        delete = await world.service.delete(task.id)
        assert isinstance(edit, Failed) and edit.code == "NOT_EDITABLE"
        assert isinstance(delete, Failed) and delete.code == "NOT_DELETABLE"


async def test_completing_records_whether_the_measure_worked(world: World) -> None:
    await world.service.ensure_day()
    task = (await world.today())[0]
    assert await world.service.complete(task.id, True) == Done(task.id)
    assert await world.service.complete(task.id, False) == Done(task.id, already=True)
    [completed] = await world.events("engagement.task_completed")
    assert completed["task_id"] == str(task.id) and completed["effective"] is True
    done = await world.tasks.get(task.id)
    assert done is not None and done.status == "COMPLETED" and done.effective is True


async def test_blocking_keeps_the_task_and_needs_a_reason(world: World) -> None:
    await world.service.ensure_day()
    task = (await world.today())[0]
    empty = await world.service.block(task.id, "  ")
    assert isinstance(empty, Failed) and empty.code == "REASON_REQUIRED"
    assert await world.service.block(task.id, "No blood pressure monitor") == Done(task.id)
    blocked = await world.tasks.get(task.id)
    assert blocked is not None and (blocked.status, blocked.blocked_reason) == (
        "BLOCKED",
        "No blood pressure monitor",
    )
    assert (await world.events("engagement.task_blocked"))[0][
        "reason"
    ] == "No blood pressure monitor"


async def test_snoozing_moves_the_due_time(world: World) -> None:
    await world.service.ensure_day()
    task = (await world.today())[0]
    assert await world.service.snooze(task.id, 15) == Done(task.id)
    moved = await world.tasks.get(task.id)
    assert moved is not None and moved.due_at == task.due_at + timedelta(minutes=15)
    bad = await world.service.snooze(task.id, 0)
    assert isinstance(bad, Failed) and bad.code == "INVALID_MINUTES"


async def test_unknown_tasks_are_typed_errors(world: World) -> None:
    for call in (
        world.service.complete(uuid4(), None),
        world.service.block(uuid4(), "x"),
        world.service.delete(uuid4()),
        world.service.snooze(uuid4(), 5),
    ):
        got = await call
        assert isinstance(got, Failed) and got.code == "NOT_FOUND"


# --- tasks born from incidents and alerts --------------------------------------------


async def test_an_incident_task_is_completed_when_its_ticket_is_resolved(world: World) -> None:
    incident, lab = uuid4(), zone_id("transit-ship", "lab")
    opened = IncidentOpened(
        incident_id=incident,
        zone_id=lab,
        severity="alert",
        title="High CO₂",
        description="d",
        source="ALERT",
    )
    await world.emit(opened)
    await world.emit(opened)  # a second delivery does not duplicate
    [task] = await world.today(kind="INCIDENT")
    assert (task.title, task.zone_id, task.incident_id) == ("Attend to: High CO₂", lab, incident)
    await world.emit(IncidentResolved(incident_id=incident, zone_id=lab, resolved_at=NOW))
    done = await world.tasks.get(task.id)
    assert done is not None and done.status == "COMPLETED"


async def test_each_recommended_action_becomes_a_measure_that_does_not_count_for_the_streak(
    world: World,
) -> None:
    alert = uuid4()
    ready = RecommendationReady(
        alert_id=alert, recommendation_id=uuid4(), action_keys=["ventilate", "filter"], citations=[]
    )
    await world.emit(ready)
    await world.emit(ready)
    measures = await world.today()
    assert sorted(t.title for t in measures) == ["Replace the filter", "Ventilate the zone"]
    assert {t.source_alert_id for t in measures} == {alert}


# --- Ground plans --------------------------------------------------------------------


async def test_a_ground_plan_applies_valid_items_and_rejects_invalid_ones_alone(
    world: World,
) -> None:
    target = uuid4()
    await world.plan(
        1,
        PlanChange(
            change="NEW",
            kind="SHIP",
            title="Check radiators",
            zone_code="eng",
            target_template_id=target,
        ),
        PlanChange(change="NEW", kind="HEALTH", title="Off the floor plan", zone_code="mars"),
    )
    [applied] = await world.events("engagement.ground_plan_applied")
    assert applied["plan_version"] == 1 and applied["applied"] == [str(target)]
    assert applied["rejected"] == [
        {"title": "Off the floor plan", "reason": "nonexistent zone 'mars'"}
    ]
    [task] = [t for t in await world.today() if t.origin == "GROUND"]
    assert task.title == "Check radiators" and task.template_id == target


async def test_delivering_the_same_plan_twice_leaves_the_tasks_once(world: World) -> None:
    change = PlanChange(change="NEW", kind="HEALTH", title="Hydration", target_template_id=uuid4())
    await world.plan(1, change)
    await world.plan(1, change)
    await world.plan(0, change)
    assert len([t for t in await world.today() if t.origin == "GROUND"]) == 1
    assert len(await world.events("engagement.ground_plan_applied")) == 1


async def test_a_new_version_keeps_what_the_crew_completed_or_created(world: World) -> None:
    target = uuid4()
    await world.plan(
        1, PlanChange(change="NEW", kind="HEALTH", title="Exercise", target_template_id=target)
    )
    ground = next(t for t in await world.today() if t.origin == "GROUND")
    await world.service.complete(ground.id, True)
    own = await world.service.create("SHIP", "Mine", None, None)
    assert isinstance(own, Done)

    await world.plan(2, PlanChange(change="CANCEL", target_template_id=target))
    still = await world.tasks.get(ground.id)
    assert still is not None and still.status == "COMPLETED", (
        "what was completed today is left untouched"
    )
    assert await world.tasks.get(own.task_id) is not None
    [status] = await GroundTemplateQuery(world.sf).list()
    assert (status.active, status.task_status, status.plan_version) == (False, "COMPLETED", 2)


async def test_ground_cannot_cancel_local_or_incident_tasks(world: World) -> None:
    await world.service.ensure_day()
    local = next(t for t in await world.today() if t.template_id is not None)
    await world.plan(1, PlanChange(change="CANCEL", target_template_id=local.template_id))
    [applied] = await world.events("engagement.ground_plan_applied")
    assert applied["applied"] == [] and "prevail" in applied["rejected"][0]["reason"]
