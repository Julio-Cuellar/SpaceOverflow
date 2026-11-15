"""Task domain: permissions by origin, streak, daily instances and applying a plan."""

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


# --- permissions and validations -------------------------------------------------------------


def test_only_crew_tasks_can_be_edited_or_deleted() -> None:
    assert [can_change(o) for o in ("CREW", "GROUND", "SYSTEM")] == [True, False, False]


@pytest.mark.parametrize(
    ("kind", "title", "error"),
    [
        ("HEALTH", "Stretch", None),
        ("INCIDENT", "x", "INVALID_KIND"),
        ("SHIP", "  ", "TITLE_REQUIRED"),
    ],
)
def test_the_crew_creates_health_or_ship_tasks_with_a_title(
    kind: str, title: str, error: str | None
) -> None:
    assert check_new_task(kind, title) == error


def test_blocking_needs_a_reason_and_a_task_not_completed() -> None:
    assert check_block("PENDING", "No sensor") is None
    assert check_block("PENDING", "   ") == "REASON_REQUIRED"
    assert check_block("COMPLETED", "x") == "ALREADY_COMPLETED"


# --- streak -------------------------------------------------------------------------------


def facts(**kw: object) -> TaskFacts:
    base: dict[str, object] = dict(
        kind="HEALTH", origin="SYSTEM", status="COMPLETED", source_alert_id=None
    )
    return TaskFacts(**{**base, **kw})  # type: ignore[arg-type]


def test_only_completed_health_routines_count_for_the_streak() -> None:
    assert counts_for_streak(facts())
    assert counts_for_streak(facts(origin="CREW"))
    assert not counts_for_streak(facts(status="PENDING"))
    assert not counts_for_streak(facts(kind="SHIP"))
    assert not counts_for_streak(facts(origin="GROUND"))
    assert not counts_for_streak(facts(source_alert_id=uuid4())), "an alert is not gamified"
    assert streak([facts(), facts(kind="INCIDENT"), facts()]) == 2


# --- daily instances ------------------------------------------------------------------


def template(**kw: object) -> Template:
    base: dict[str, object] = dict(
        id=uuid4(),
        kind="HEALTH",
        title="Exercise",
        recurrence="DAILY",
        zone_code=None,
        origin="SYSTEM",
        active=True,
        due_time="18:00",
    )
    return Template(**{**base, **kw})  # type: ignore[arg-type]


def test_active_daily_templates_get_one_instance_per_day() -> None:
    daily, once, off = template(), template(recurrence="ONCE"), template(active=False)
    due = due_instances([daily, once, off], date(2026, 11, 15), today=set(), ever=set())
    assert [t.id for t in due] == [daily.id, once.id]
    again = due_instances([daily, once], date(2026, 11, 15), today={daily.id}, ever={daily.id})
    assert [t.id for t in again] == [once.id]
    tomorrow = due_instances([daily, once], date(2026, 11, 16), today=set(), ever={once.id})
    assert [t.id for t in tomorrow] == [daily.id], "a one-time task does not repeat"


# --- applying a Ground plan -----------------------------------------------------------


def item(change: str, **kw: object) -> PlanItem:
    base: dict[str, object] = dict(
        kind=None, title=None, recurrence=None, zone_code=None, target_template_id=None
    )
    return PlanItem(change=change, **{**base, **kw})  # type: ignore[arg-type]


def test_new_items_create_ground_templates() -> None:
    target = uuid4()
    new = item("NEW", kind="SHIP", title="Check seals", zone_code="air", target_template_id=target)
    actions, rejected = plan_actions([new], {}, ZONES)
    assert rejected == [] and [(a.change, a.template_id) for a in actions] == [("NEW", target)]
    assert actions[0].recurrence == "DAILY", "repeats every day by default"


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (item("NEW", kind="INCIDENT", title="x"), "kind"),
        (item("NEW", kind="HEALTH", title=" "), "title"),
        (item("NEW", kind="HEALTH", title="x", zone_code="mars"), "zone"),
        (item("NEW", kind="HEALTH", title="x", recurrence="EVERY_HOUR"), "recurrence"),
        (item("UPDATE", target_template_id=uuid4(), title="x"), "does not exist"),
        (item("CANCEL"), "does not exist"),
    ],
)
def test_an_invalid_item_is_rejected_alone_with_its_reason(bad: PlanItem, reason: str) -> None:
    good = item("NEW", kind="HEALTH", title="Stretch")
    actions, rejected = plan_actions([bad, good], {}, ZONES)
    assert len(actions) == 1 and actions[0].title == "Stretch"
    assert len(rejected) == 1 and reason in rejected[0].reason


def test_ground_cannot_change_or_cancel_local_templates() -> None:
    local = uuid4()
    templates = {local: TemplateState(local, "SYSTEM", active=True)}
    for change in ("UPDATE", "CANCEL"):
        actions, rejected = plan_actions(
            [item(change, target_template_id=local, title="x")], templates, ZONES
        )
        assert actions == [] and "Ground" in rejected[0].reason


def test_updates_and_cancellations_of_ground_templates_apply() -> None:
    mine = uuid4()
    templates = {mine: TemplateState(mine, "GROUND", active=True)}
    actions, rejected = plan_actions(
        [
            item("UPDATE", target_template_id=mine, title="New"),
            item("CANCEL", target_template_id=mine),
        ],
        templates,
        ZONES,
    )
    assert rejected == [] and [a.change for a in actions] == ["UPDATE", "CANCEL"]


def test_a_new_item_cannot_reuse_an_existing_template_id() -> None:
    mine = uuid4()
    templates = {mine: TemplateState(mine, "GROUND", active=True)}
    _, rejected = plan_actions(
        [item("NEW", kind="HEALTH", title="x", target_template_id=mine)], templates, ZONES
    )
    assert "already exists" in rejected[0].reason
