"""Facility domain: floor plan, type catalog and decisions about tickets and zones."""

from __future__ import annotations

from pathlib import Path

import pytest

from spaceapp.modules.facility.adapters.outbound.json_data import load_catalog, load_plan
from spaceapp.modules.facility.domain.catalog import IncidentCatalog, IncidentType, InvalidCatalog
from spaceapp.modules.facility.domain.incidents import (
    OpenTicket,
    describe,
    incident_code,
    on_alert,
    opens_ticket,
    resolve_check,
    zone_status,
)
from spaceapp.modules.facility.domain.plan import InvalidPlan, Plan, ZonePlan
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog as rules
from spaceapp.platform.ids import zone_id

ROOT = Path(__file__).resolve().parents[3]
PLAN = load_plan(ROOT / "data" / "facility" / "plan.json")
CATALOG = load_catalog(ROOT / "data" / "facility" / "incident_types.json")
RULES = rules(ROOT / "rules" / "catalog" / "monitoring.json")


# --- floor plan -------------------------------------------------------------------------------


def test_the_plan_has_the_ten_zones_the_simulator_uses() -> None:
    import json

    sim = json.loads((ROOT / "data" / "telemetry" / "sim_layout.json").read_text())
    assert [z.code for z in PLAN.zones] == [z["code"] for z in sim["zones"]]
    assert PLAN.habitat_code == sim["habitat_code"]


def test_zone_ids_are_the_stable_ids_telemetry_uses() -> None:
    lab = PLAN.zone("lab")
    assert lab is not None and lab.id == zone_id("transit-ship", "lab")
    assert PLAN.zone("nope") is None


def test_a_plan_with_repeated_zone_codes_is_rejected() -> None:
    z = ZonePlan("lab", "Laboratory", "laboratory", 1, {"x": 0, "y": 0, "w": 1, "h": 1})
    with pytest.raises(InvalidPlan, match="lab"):
        Plan("h", "H", "ship", 101.3, (z, z))


# --- catalog ----------------------------------------------------------------------------


def test_the_catalog_has_61_types_in_12_categories() -> None:
    assert len(CATALOG.types) == 61 and len(CATALOG.categories) == 12


def test_every_rule_of_an_auto_type_exists_or_is_explicitly_pending() -> None:
    known = {r.key for r in RULES.rules}
    for t in CATALOG.types:
        for key in t.rule_keys:
            assert key in known or key in CATALOG.pending_rules, f"{t.key}: {key}"
    assert not (CATALOG.pending_rules & known), "a rule that already exists cannot stay pending"


def test_every_monitoring_rule_maps_to_exactly_one_incident_type() -> None:
    for rule in RULES.rules:
        found = CATALOG.type_for_rule(rule.key)
        assert found is not None and found.detection == "AUTO", rule.key


def test_typical_zones_are_known_zone_codes_or_any() -> None:
    codes = {z.code for z in PLAN.zones} | {"*"}
    assert all(set(t.typical_zones) <= codes for t in CATALOG.types)


def _type(**kw: object) -> IncidentType:
    base: dict[str, object] = dict(
        key="k",
        category="atm",
        name="N",
        detection="MANUAL",
        rule_keys=(),
        default_severity="alert",
        evidence_state="DEMO",
        typical_zones=("*",),
        suggested_actions=(),
    )
    return IncidentType(**{**base, **kw})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"category": "zzz"}, "category"),
        ({"default_severity": "grave"}, "severity"),
        ({"detection": "AUTO"}, "rule"),
        ({"rule_keys": ("r",)}, "MANUAL"),
        ({"evidence_state": "X"}, "evidence"),
    ],
)
def test_invalid_types_are_rejected(kw: dict[str, object], message: str) -> None:
    with pytest.raises(InvalidCatalog, match=message):
        IncidentCatalog("v", {"atm": "Atmosphere"}, (_type(**kw),), frozenset())


def test_a_rule_cannot_belong_to_two_types() -> None:
    a = _type(key="a", detection="AUTO", rule_keys=("r",))
    b = _type(key="b", detection="AUTO", rule_keys=("r",))
    with pytest.raises(InvalidCatalog, match="r"):
        IncidentCatalog("v", {"atm": "A"}, (a, b), frozenset())


# --- tickets and zones ---------------------------------------------------------------------


def test_only_alert_or_worse_opens_a_ticket() -> None:
    assert [opens_ticket(s) for s in ("attention", "alert", "critical")] == [False, True, True]


def test_an_alert_opens_escalates_or_annotates_the_zone_ticket() -> None:
    ticket = OpenTicket(severity="alert", source="ALERT", status="open")
    assert on_alert(None, "attention") == "ignore"
    assert on_alert(None, "alert") == "open"
    assert on_alert(ticket, "alert") == "note"
    assert on_alert(ticket, "critical") == "escalate"
    assert on_alert(OpenTicket("critical", "ALERT", "acknowledged"), "alert") == "note"


def test_zone_status_is_the_worst_of_active_alerts_and_open_tickets() -> None:
    assert zone_status([], []) == "normal"
    assert zone_status(["attention"], []) == "attention"
    assert zone_status(["attention"], ["critical"]) == "critical"
    assert zone_status(["critical", "alert"], ["alert"]) == "critical"


def test_an_automatic_ticket_cannot_be_resolved_while_its_zone_has_active_alerts() -> None:
    assert resolve_check("ALERT", "open", active_alerts=1) == "ACTIVE_ALERTS"
    assert resolve_check("ALERT", "acknowledged", active_alerts=0) is None
    assert resolve_check("MANUAL", "open", active_alerts=2) is None
    assert resolve_check("MANUAL", "resolved", active_alerts=0) == "ALREADY_RESOLVED"


def test_the_description_says_what_where_value_limit_and_source() -> None:
    text = describe(
        "High CO₂",
        "Laboratory",
        {
            "parameter": "ppco2",
            "value": 3.4,
            "unit": "mmHg",
            "operator": ">",
            "threshold": 3.0,
            "window_s": 3600,
            "source_requirement": "V2 6.2.1",
            "source_document": "NASA-STD-3001",
            "evidence_state": "VERIFIED",
        },
    )
    assert text == (
        "High CO₂ in Laboratory: ppco2 = 3.4 mmHg (limit > 3.0, window 3600 s). "
        "Source: NASA-STD-3001 V2 6.2.1 [VERIFIED]."
    )


def test_the_description_tolerates_missing_evidence() -> None:
    assert describe("High CO₂", "Laboratory", {}) == "High CO₂ in Laboratory."


def test_the_incident_code_is_a_padded_sequence_number() -> None:
    assert [incident_code(n) for n in (1, 42, 9999, 12345)] == [
        "INC-0001",
        "INC-0042",
        "INC-9999",
        "INC-12345",
    ]
