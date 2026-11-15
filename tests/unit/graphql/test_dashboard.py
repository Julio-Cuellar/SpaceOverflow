"""Cabin vital signs: value, severity and zone from readings and active alerts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from spaceapp.interfaces.graphql.dashboard import build_dashboard
from spaceapp.modules.monitoring.facade import ActiveAlertView, RuleView
from spaceapp.modules.telemetry.facade import LatestReadingView

T = datetime(2026, 11, 14, 20, 0, tzinfo=UTC)
LAB, ENG = UUID(int=1), UUID(int=2)


def reading(zone: UUID, metric: str, value: float, unit: str = "u") -> LatestReadingView:
    return LatestReadingView(zone, metric, unit, "cabin", "SIMULATED", value, T)


def cabin(zone: UUID, co2: float = 0.7) -> list[LatestReadingView]:
    return [
        reading(zone, "pressure_kpa", 101.3, "kPa"),
        reading(zone, "o2_pct", 21.0, "%"),
        reading(zone, "co2_mmhg", co2, "mmHg"),
        reading(zone, "temperature_c", 22.0, "°C"),
        reading(zone, "humidity_pct", 45.0, "%"),
    ]


def rule(key: str, parameter: str, severity: str, evidence: str = "VERIFIED") -> RuleView:
    return RuleView(
        key,
        parameter,
        severity,
        "req",
        "doc",
        evidence,
        "act",
        "hrp",
        "threshold",
        ">",
        1.0,
        "u",
        0,
    )


RULES = {
    r.key: r
    for r in (
        rule("env-co2-1h", "ppco2", "alert"),
        rule("env-co2-crit", "ppco2", "critical"),
        rule("env-trend-t", "temperature_c", "attention", "DEMO"),
        rule("env-n2", "n2_pct", "alert", "TB"),
    )
}


def active(key: str, zone: UUID | None, severity: str) -> ActiveAlertView:
    r = RULES[key]
    return ActiveAlertView(uuid4(), key, zone, severity, "raised", T, r.evidence_state, "act")


def test_without_readings_there_are_no_vitals_and_the_state_is_normal() -> None:
    severity, vitals = build_dashboard([], [], RULES)
    assert severity == "normal" and vitals == []


def test_without_alerts_each_vital_is_the_mean_of_the_zones_and_has_no_zone() -> None:
    _, vitals = build_dashboard(cabin(LAB, co2=0.6) + cabin(ENG, co2=1.0), [], RULES)
    co2 = next(v for v in vitals if v.key == "co2_mmhg")
    assert co2.value == pytest.approx(0.8)
    assert co2.severity == "normal" and co2.zone_id is None and co2.unit == "mmHg"
    assert [v.key for v in vitals] == [
        "pressure_kpa",
        "o2_pct",
        "co2_mmhg",
        "temperature_c",
        "humidity_pct",
        "pio2",
    ]


def test_pio2_is_derived_from_pressure_and_oxygen() -> None:
    _, vitals = build_dashboard(cabin(LAB), [], RULES)
    pio2 = next(v for v in vitals if v.key == "pio2")
    assert pio2.unit == "mmHg" and pio2.value == pytest.approx(149.7, abs=0.1)
    assert pio2.origin == "SIMULATED"


def test_the_worst_alert_sets_severity_zone_value_and_evidence_of_its_vital() -> None:
    alerts = [active("env-co2-1h", ENG, "alert"), active("env-co2-crit", LAB, "critical")]
    severity, vitals = build_dashboard(cabin(LAB, co2=4.2) + cabin(ENG, co2=3.1), alerts, RULES)
    co2 = next(v for v in vitals if v.key == "co2_mmhg")
    assert (co2.severity, co2.zone_id, co2.value) == ("critical", LAB, 4.2)
    assert co2.evidence_state == "VERIFIED"
    assert severity == "critical"
    assert next(v for v in vitals if v.key == "humidity_pct").severity == "normal"


def test_an_alert_on_a_parameter_without_vital_still_counts_for_the_global_state() -> None:
    severity, vitals = build_dashboard(cabin(LAB), [active("env-n2", LAB, "alert")], RULES)
    assert severity == "alert"
    assert all(v.severity == "normal" for v in vitals)


def test_a_vital_without_alert_takes_the_strongest_evidence_of_its_rules() -> None:
    _, vitals = build_dashboard(cabin(LAB), [], RULES)
    by_key = {v.key: v for v in vitals}
    assert by_key["co2_mmhg"].evidence_state == "VERIFIED"
    assert by_key["temperature_c"].evidence_state == "DEMO"
    assert by_key["humidity_pct"].evidence_state == "DEMO"  # no rules: demo data
