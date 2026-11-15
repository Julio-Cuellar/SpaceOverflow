"""Ground link domain: integrity, versions and stages of a published plan."""

from __future__ import annotations

from uuid import UUID

from spaceapp.modules.groundlink.domain.plans import (
    DraftItem,
    ShipTemplate,
    draft_templates,
    in_flight,
    inbound_decision,
    plan_hash,
)

ITEMS = [{"change": "NEW", "kind": "HEALTH", "title": "Exercise"}]


def test_the_hash_covers_version_and_items_and_ignores_key_order() -> None:
    a = plan_hash(3, ITEMS)
    assert a == plan_hash(3, [{"title": "Exercise", "kind": "HEALTH", "change": "NEW"}])
    assert a != plan_hash(4, ITEMS)
    assert a != plan_hash(3, [{**ITEMS[0], "title": "Other"}])
    assert len(a) == 64


def test_a_plan_is_received_ignored_or_rejected() -> None:
    good = plan_hash(3, ITEMS)
    assert inbound_decision(3, ITEMS, good, last_version=2) == ("received", None)
    assert inbound_decision(3, ITEMS, good, last_version=None) == ("received", None)
    assert inbound_decision(2, ITEMS, plan_hash(2, ITEMS), last_version=2) == ("ignored", None)
    assert inbound_decision(1, ITEMS, plan_hash(1, ITEMS), last_version=2) == ("ignored", None)
    decision, reason = inbound_decision(3, ITEMS, "f" * 64, last_version=2)
    assert decision == "rejected" and reason is not None and "integrity" in reason


def test_a_plan_is_in_flight_until_it_is_confirmed_or_rejected() -> None:
    assert [in_flight(s) for s in ("QUEUED", "IN_TRANSIT", "RECEIVED", "APPLIED")] == [True] * 4
    assert [in_flight(s) for s in ("DRAFT", "CONFIRMED", "REJECTED")] == [False] * 3


def test_the_draft_shows_active_templates_marked_for_cancel_and_the_new_ones() -> None:
    a, b, c = UUID(int=1), UUID(int=2), UUID(int=3)
    active = [ShipTemplate(a, "Exercise", "HEALTH", "COMPLETED", None)]
    active.append(ShipTemplate(b, "Filters", "SHIP", "BLOCKED", "No spare part"))
    items = [DraftItem("CANCEL", b, None, None), DraftItem("NEW", c, "Sleep", "HEALTH")]
    shown = draft_templates(active, items)
    assert [(t.id, t.status, t.cancelled) for t in shown] == [
        (a, "COMPLETED", False),
        (b, "BLOCKED", True),
        (c, "PENDING", False),
    ]
    assert shown[1].blocked_reason == "No spare part"
