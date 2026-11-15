"""Misiones y tareas sobre PostgreSQL real: criterios de aceptación de F10 y aplicación de planes."""

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
TITLES = {"ventilar": "Ventilar la zona", "filtro": "Cambiar el filtro"}


class World:
    def __init__(self, sf: Any) -> None:
        self.sf = sf
        self.service = EngagementService(
            sf,
            SqlEngagementRepository,
            system_templates=load_system_templates(ROOT / "data" / "engagement" / "templates.json"),
            zone_codes=ZONES,
            zone_id_of=lambda code: zone_id("nave-transito", code),
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


# --- tareas del día ----------------------------------------------------------------------


async def test_each_system_template_gets_one_task_per_day(world: World) -> None:
    await world.service.ensure_day()
    await world.service.ensure_day()
    tasks = await world.today()
    assert len(tasks) == 7 and {t.origin for t in tasks} == {"SISTEMA"}
    assert {t.kind for t in tasks} == {"SALUD", "NAVE"}
    assert len(await world.events("engagement.task_assigned")) == 7
    sellos = next(t for t in tasks if "esclusa" in t.title)
    assert sellos.zone_id == zone_id("nave-transito", "air")
    assert sellos.due_at == NOW.replace(hour=9)


# --- tareas propias ----------------------------------------------------------------------


async def test_the_crew_creates_its_own_task_without_any_ground_link(world: World) -> None:
    got = await world.service.create("SALUD", " Estirar la espalda ", None, None)
    assert isinstance(got, Done)
    task = await world.tasks.get(got.task_id)
    assert task is not None and (task.origin, task.title, task.status) == (
        "TRIPULACION",
        "Estirar la espalda",
        "PENDIENTE",
    )
    [created] = await world.events("engagement.task_created")
    assert created["origin"] == "TRIPULACION"
    bad = await world.service.create("INCIDENTE", "x", None, None)
    assert isinstance(bad, Failed) and bad.code == "INVALID_KIND"


async def test_crew_tasks_can_be_edited_and_deleted(world: World) -> None:
    got = await world.service.create("NAVE", "Limpiar", None, None)
    assert isinstance(got, Done)
    lab = zone_id("nave-transito", "lab")
    assert await world.service.update(
        got.task_id, title="Limpiar el lab", zone_id=lab, due_at=None
    ) == Done(got.task_id)
    task = await world.tasks.get(got.task_id)
    assert task is not None and (task.title, task.zone_id) == ("Limpiar el lab", lab)
    assert await world.service.delete(got.task_id) == Done(got.task_id)
    assert await world.tasks.get(got.task_id) is None


async def test_system_and_ground_tasks_reject_edit_and_delete_with_a_typed_error(
    world: World,
) -> None:
    await world.plan(1, PlanChange(change="NEW", kind="SALUD", title="Ejercicio de Tierra"))
    await world.service.ensure_day()
    for origin in ("TIERRA", "SISTEMA"):
        task = (await world.today(kind="SALUD"))[0] if origin == "SISTEMA" else None
        task = task or next(t for t in await world.today() if t.origin == "TIERRA")
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
    assert done is not None and done.status == "COMPLETADA" and done.effective is True


async def test_blocking_keeps_the_task_and_needs_a_reason(world: World) -> None:
    await world.service.ensure_day()
    task = (await world.today())[0]
    empty = await world.service.block(task.id, "  ")
    assert isinstance(empty, Failed) and empty.code == "REASON_REQUIRED"
    assert await world.service.block(task.id, "Sin tensiómetro") == Done(task.id)
    blocked = await world.tasks.get(task.id)
    assert blocked is not None and (blocked.status, blocked.blocked_reason) == (
        "BLOQUEADA",
        "Sin tensiómetro",
    )
    assert (await world.events("engagement.task_blocked"))[0]["reason"] == "Sin tensiómetro"


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


# --- tareas que nacen de incidentes y alertas --------------------------------------------


async def test_an_incident_task_is_completed_when_its_ticket_is_resolved(world: World) -> None:
    incident, lab = uuid4(), zone_id("nave-transito", "lab")
    opened = IncidentOpened(
        incident_id=incident,
        zone_id=lab,
        severity="alerta",
        title="CO₂ alto",
        description="d",
        source="ALERTA",
    )
    await world.emit(opened)
    await world.emit(opened)  # una segunda entrega no duplica
    [task] = await world.today(kind="INCIDENTE")
    assert (task.title, task.zone_id, task.incident_id) == ("Atender: CO₂ alto", lab, incident)
    await world.emit(IncidentResolved(incident_id=incident, zone_id=lab, resolved_at=NOW))
    done = await world.tasks.get(task.id)
    assert done is not None and done.status == "COMPLETADA"


async def test_each_recommended_action_becomes_a_measure_that_does_not_count_for_the_streak(
    world: World,
) -> None:
    alert = uuid4()
    ready = RecommendationReady(
        alert_id=alert, recommendation_id=uuid4(), action_keys=["ventilar", "filtro"], citations=[]
    )
    await world.emit(ready)
    await world.emit(ready)
    measures = await world.today()
    assert sorted(t.title for t in measures) == ["Cambiar el filtro", "Ventilar la zona"]
    assert {t.source_alert_id for t in measures} == {alert}


# --- planes de Tierra --------------------------------------------------------------------


async def test_a_ground_plan_applies_valid_items_and_rejects_invalid_ones_alone(
    world: World,
) -> None:
    target = uuid4()
    await world.plan(
        1,
        PlanChange(
            change="NEW",
            kind="NAVE",
            title="Revisar radiadores",
            zone_code="eng",
            target_template_id=target,
        ),
        PlanChange(change="NEW", kind="SALUD", title="Fuera del plano", zone_code="marte"),
    )
    [applied] = await world.events("engagement.ground_plan_applied")
    assert applied["plan_version"] == 1 and applied["applied"] == [str(target)]
    assert applied["rejected"] == [
        {"title": "Fuera del plano", "reason": "zona inexistente 'marte'"}
    ]
    [task] = [t for t in await world.today() if t.origin == "TIERRA"]
    assert task.title == "Revisar radiadores" and task.template_id == target


async def test_delivering_the_same_plan_twice_leaves_the_tasks_once(world: World) -> None:
    change = PlanChange(change="NEW", kind="SALUD", title="Hidratación", target_template_id=uuid4())
    await world.plan(1, change)
    await world.plan(1, change)
    await world.plan(0, change)
    assert len([t for t in await world.today() if t.origin == "TIERRA"]) == 1
    assert len(await world.events("engagement.ground_plan_applied")) == 1


async def test_a_new_version_keeps_what_the_crew_completed_or_created(world: World) -> None:
    target = uuid4()
    await world.plan(
        1, PlanChange(change="NEW", kind="SALUD", title="Ejercicio", target_template_id=target)
    )
    ground = next(t for t in await world.today() if t.origin == "TIERRA")
    await world.service.complete(ground.id, True)
    own = await world.service.create("NAVE", "Mía", None, None)
    assert isinstance(own, Done)

    await world.plan(2, PlanChange(change="CANCEL", target_template_id=target))
    still = await world.tasks.get(ground.id)
    assert still is not None and still.status == "COMPLETADA", "lo completado hoy no se toca"
    assert await world.tasks.get(own.task_id) is not None
    [status] = await GroundTemplateQuery(world.sf).list()
    assert (status.active, status.task_status, status.plan_version) == (False, "COMPLETADA", 2)


async def test_ground_cannot_cancel_local_or_incident_tasks(world: World) -> None:
    await world.service.ensure_day()
    local = next(t for t in await world.today() if t.template_id is not None)
    await world.plan(1, PlanChange(change="CANCEL", target_template_id=local.template_id))
    [applied] = await world.events("engagement.ground_plan_applied")
    assert applied["applied"] == [] and "prevalecen" in applied["rejected"][0]["reason"]
