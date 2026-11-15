"""Dominio de tareas: permisos por origen, racha, instancias del día y aplicación de un plan."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from spaceapp.modules.engagement.domain.plans import PlanItem, TemplateState, plan_actions
from spaceapp.modules.engagement.domain.tasks import (
    TaskFacts,
    Template,
    can_change,
    check_block,
    check_new_task,
    counts_for_streak,
    due_instances,
    streak,
)

ZONES = {"lab", "air"}


# --- permisos y validaciones -------------------------------------------------------------


def test_only_crew_tasks_can_be_edited_or_deleted() -> None:
    assert [can_change(o) for o in ("TRIPULACION", "TIERRA", "SISTEMA")] == [True, False, False]


@pytest.mark.parametrize(
    ("kind", "title", "error"),
    [
        ("SALUD", "Estirar", None),
        ("INCIDENTE", "x", "INVALID_KIND"),
        ("NAVE", "  ", "TITLE_REQUIRED"),
    ],
)
def test_the_crew_creates_health_or_ship_tasks_with_a_title(
    kind: str, title: str, error: str | None
) -> None:
    assert check_new_task(kind, title) == error


def test_blocking_needs_a_reason_and_a_task_not_completed() -> None:
    assert check_block("PENDIENTE", "Sin sensor") is None
    assert check_block("PENDIENTE", "   ") == "REASON_REQUIRED"
    assert check_block("COMPLETADA", "x") == "ALREADY_COMPLETED"


# --- racha -------------------------------------------------------------------------------


def facts(**kw: object) -> TaskFacts:
    base: dict[str, object] = dict(
        kind="SALUD", origin="SISTEMA", status="COMPLETADA", source_alert_id=None
    )
    return TaskFacts(**{**base, **kw})  # type: ignore[arg-type]


def test_only_completed_health_routines_count_for_the_streak() -> None:
    assert counts_for_streak(facts())
    assert counts_for_streak(facts(origin="TRIPULACION"))
    assert not counts_for_streak(facts(status="PENDIENTE"))
    assert not counts_for_streak(facts(kind="NAVE"))
    assert not counts_for_streak(facts(origin="TIERRA"))
    assert not counts_for_streak(facts(source_alert_id=uuid4())), "una alerta no se gamifica"
    assert streak([facts(), facts(kind="INCIDENTE"), facts()]) == 2


# --- instancias del día ------------------------------------------------------------------


def template(**kw: object) -> Template:
    base: dict[str, object] = dict(
        id=uuid4(),
        kind="SALUD",
        title="Ejercicio",
        recurrence="DIARIA",
        zone_code=None,
        origin="SISTEMA",
        active=True,
        due_time="18:00",
    )
    return Template(**{**base, **kw})  # type: ignore[arg-type]


def test_active_daily_templates_get_one_instance_per_day() -> None:
    daily, once, off = template(), template(recurrence="UNA_VEZ"), template(active=False)
    due = due_instances([daily, once, off], date(2026, 11, 15), today=set(), ever=set())
    assert [t.id for t in due] == [daily.id, once.id]
    again = due_instances([daily, once], date(2026, 11, 15), today={daily.id}, ever={daily.id})
    assert [t.id for t in again] == [once.id]
    tomorrow = due_instances([daily, once], date(2026, 11, 16), today=set(), ever={once.id})
    assert [t.id for t in tomorrow] == [daily.id], "una tarea de una vez no se repite"


# --- aplicar un plan de Tierra -----------------------------------------------------------


def item(change: str, **kw: object) -> PlanItem:
    base: dict[str, object] = dict(
        kind=None, title=None, recurrence=None, zone_code=None, target_template_id=None
    )
    return PlanItem(change=change, **{**base, **kw})  # type: ignore[arg-type]


def test_new_items_create_ground_templates() -> None:
    target = uuid4()
    new = item(
        "NEW", kind="NAVE", title="Revisar sellos", zone_code="air", target_template_id=target
    )
    actions, rejected = plan_actions([new], {}, ZONES)
    assert rejected == [] and [(a.change, a.template_id) for a in actions] == [("NEW", target)]
    assert actions[0].recurrence == "DIARIA", "por defecto se repite cada día"


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (item("NEW", kind="INCIDENTE", title="x"), "tipo"),
        (item("NEW", kind="SALUD", title=" "), "título"),
        (item("NEW", kind="SALUD", title="x", zone_code="marte"), "zona"),
        (item("NEW", kind="SALUD", title="x", recurrence="CADA_HORA"), "recurrencia"),
        (item("UPDATE", target_template_id=uuid4(), title="x"), "no existe"),
        (item("CANCEL"), "no existe"),
    ],
)
def test_an_invalid_item_is_rejected_alone_with_its_reason(bad: PlanItem, reason: str) -> None:
    good = item("NEW", kind="SALUD", title="Estirar")
    actions, rejected = plan_actions([bad, good], {}, ZONES)
    assert len(actions) == 1 and actions[0].title == "Estirar"
    assert len(rejected) == 1 and reason in rejected[0].reason


def test_ground_cannot_change_or_cancel_local_templates() -> None:
    local = uuid4()
    templates = {local: TemplateState(local, "SISTEMA", active=True)}
    for change in ("UPDATE", "CANCEL"):
        actions, rejected = plan_actions(
            [item(change, target_template_id=local, title="x")], templates, ZONES
        )
        assert actions == [] and "Tierra" in rejected[0].reason


def test_updates_and_cancellations_of_ground_templates_apply() -> None:
    mine = uuid4()
    templates = {mine: TemplateState(mine, "TIERRA", active=True)}
    actions, rejected = plan_actions(
        [
            item("UPDATE", target_template_id=mine, title="Nuevo"),
            item("CANCEL", target_template_id=mine),
        ],
        templates,
        ZONES,
    )
    assert rejected == [] and [a.change for a in actions] == ["UPDATE", "CANCEL"]


def test_a_new_item_cannot_reuse_an_existing_template_id() -> None:
    mine = uuid4()
    templates = {mine: TemplateState(mine, "TIERRA", active=True)}
    _, rejected = plan_actions(
        [item("NEW", kind="SALUD", title="x", target_template_id=mine)], templates, ZONES
    )
    assert "ya existe" in rejected[0].reason
