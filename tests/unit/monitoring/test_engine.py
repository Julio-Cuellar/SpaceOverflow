import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.domain.engine import derive_series, evaluate
from spaceapp.modules.monitoring.domain.series import Sample
from spaceapp.modules.monitoring.domain.units import kpa_to_psi, psi_to_kpa

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
RULES = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json").rules
ZONE = uuid4()


def flat(value: float, seconds: int = 60, step: int = 1) -> list[Sample]:
    return [Sample(NOW - timedelta(seconds=s), value) for s in range(seconds, -1, -step)][::1]


def nominal(*, seconds: int = 60, step: int = 1, **over: float) -> dict[str, list[Sample]]:
    base = {
        "pressure_kpa": 101.3,
        "o2_pct": 21.0,
        "co2_mmhg": 0.6,
        "temperature_c": 22.0,
        "humidity_pct": 45.0,
    }
    base.update(over)
    return {k: flat(v, seconds, step) for k, v in base.items()}


def hour(**over: float) -> dict[str, list[Sample]]:
    return nominal(seconds=3600, step=10, **over)


def run(raw, *, scale: float = 1.0, rules=RULES):
    return evaluate(ZONE, raw, rules, NOW, window_scale=scale)


def keys(result) -> set[str]:
    return {h.rule_key for h in result.hits}


def by_key(result, key: str):
    return next(h for h in result.hits if h.rule_key == key)


def test_a_nominal_cabin_has_no_hits():
    assert run(hour()).hits == []


def test_derived_pio2_uses_total_pressure_and_o2_fraction():
    pio2 = derive_series(nominal())["pio2"][-1].value
    assert pio2 == pytest.approx(149.7, abs=0.2)  # vector 1


def test_vector_2_o2_18_percent_is_a_proposed_band_warning_just_above_127():
    r = run(nominal(o2_pct=18.0))
    assert keys(r) == {"env-pio2-low-pre"}
    h = by_key(r, "env-pio2-low-pre")
    assert (h.severity, h.evidence_state) == ("attention", "DEMO")
    assert h.value == pytest.approx(128.3, abs=0.2)


def test_vector_3_low_total_pressure_with_34_percent_o2_is_a_warning_near_127():
    r = run(nominal(pressure_kpa=56.5, o2_pct=34.0))
    assert keys(r) == {"env-pio2-low-pre"}
    assert by_key(r, "env-pio2-low-pre").value == pytest.approx(128.1, abs=0.2)


def test_vector_4_co2_one_hour_average_of_3_1_is_a_verified_alert():
    r = run(hour(co2_mmhg=3.1))
    assert keys(r) == {"env-co2-1h"}
    h = by_key(r, "env-co2-1h")
    assert (h.severity, h.evidence_state, h.source_requirement) == (
        "alert",
        "VERIFIED",
        "V2 6004",
    )
    assert h.value == pytest.approx(3.1)
    assert "env-co2-pre" in r.superseded


def test_vector_5_a_slow_pressure_drop_does_not_trigger_the_rate_rule():
    p = [
        Sample(NOW - timedelta(seconds=60 - i), psi_to_kpa(14.7 - 2.7 * i / 60)) for i in range(61)
    ]
    r = run({**nominal(), "pressure_kpa": p})
    assert "env-dpdt" not in keys(r)


def test_vector_6_a_14_psi_drop_in_half_a_minute_is_a_rapid_depressurization():
    start = 14.0 + 0.69
    p = [
        Sample(NOW - timedelta(seconds=30 - i), psi_to_kpa(start - 14.0 * i / 30))
        for i in range(31)
    ]
    r = run({**nominal(), "pressure_kpa": p})
    h = by_key(r, "env-dpdt")
    assert h.value == pytest.approx(28.0, rel=0.02)
    assert (h.severity, h.evidence_state) == ("alert", "VERIFIED")


def test_a_change_of_one_psi_or_less_is_exempt_even_if_it_is_fast():
    p = [Sample(NOW - timedelta(seconds=2 - i), psi_to_kpa(14.7 - 0.9 * i / 2)) for i in range(3)]
    r = run({**nominal(), "pressure_kpa": p})
    assert "env-dpdt" not in keys(r)
    assert kpa_to_psi(p[0].value) - kpa_to_psi(p[-1].value) == pytest.approx(0.9)


def test_each_zone_is_evaluated_on_its_own():
    other = uuid4()
    bad = evaluate(ZONE, hour(co2_mmhg=3.5), RULES, NOW)
    ok = evaluate(other, hour(), RULES, NOW)
    assert {h.zone_id for h in bad.hits} == {ZONE}
    assert ok.hits == []


def test_a_worse_band_supersedes_the_milder_ones():
    r = run(nominal(o2_pct=17.0))  # PIO2 ~121: below 127 (alert), 1 h window not covered
    assert "env-pio2-low" in keys(r) and "env-pio2-low-pre" not in keys(r)
    assert "env-pio2-low-pre" in r.superseded
    full = run(hour(o2_pct=17.0))  # with 1 h of data the absolute limit kicks in
    assert keys(full) == {"env-pio2-abs-low"}
    assert {"env-pio2-low", "env-pio2-low-pre"} <= full.superseded


@pytest.mark.parametrize(
    ("over", "expected"),
    [
        ({"pressure_kpa": 30.0, "o2_pct": 60.0}, "env-ptotal-low"),
        ({"pressure_kpa": 105.0}, "env-ptotal-high"),
        ({"o2_pct": 75.0}, "env-n2"),
        ({"humidity_pct": 82.0}, "env-rh-high"),
        ({"humidity_pct": 65.0}, "env-rh-high-pre"),
        ({"humidity_pct": 28.0}, "env-rh-low-pre"),
        ({"humidity_pct": 20.0}, "env-rh-low"),
        ({"temperature_c": 29.0}, "env-t-high"),
        ({"temperature_c": 26.0}, "env-t-high-pre"),
        ({"temperature_c": 19.0}, "env-t-low-pre"),
        ({"temperature_c": 17.0}, "env-t-low"),
    ],
)
def test_each_environment_limit_raises_its_own_rule(over, expected):
    assert expected in keys(run(nominal(**over)))


def test_inactive_rules_are_ignored():
    off = tuple(
        r.__class__(**{**r.__dict__, "active": False}) if r.key == "env-rh-high" else r
        for r in RULES
    )
    assert "env-rh-high" not in keys(run(nominal(humidity_pct=82.0), rules=off))


def test_a_windowed_rule_needs_the_window_to_be_covered_by_data():
    short = nominal(co2_mmhg=3.5)  # only 60 s of data
    assert "env-co2-1h" not in keys(run(short))
    assert "env-co2-1h" in keys(run(short, scale=1 / 60))  # demo time


def test_a_trend_warns_before_any_threshold_is_crossed():
    rng = random.Random(3)
    co2 = [0.7 + rng.gauss(0, 0.03) for _ in range(120)]
    co2[-10:] = [v + 1.2 for v in co2[-10:]]
    series = [Sample(NOW - timedelta(seconds=119 - i), v) for i, v in enumerate(co2)]
    r = run({**nominal(seconds=119), "co2_mmhg": series})
    assert keys(r) == {"env-trend-co2"}
    h = by_key(r, "env-trend-co2")
    assert (h.severity, h.evidence_state) == ("attention", "DEMO")


def test_a_trend_is_not_reported_when_a_threshold_rule_already_covers_that_parameter():
    rng = random.Random(3)
    co2 = [0.7 + rng.gauss(0, 0.03) for _ in range(120)]
    co2[-10:] = [4.0] * 10
    series = [Sample(NOW - timedelta(seconds=119 - i), v) for i, v in enumerate(co2)]
    r = run({**nominal(seconds=119), "co2_mmhg": series}, scale=1 / 3600)
    assert not any(k.startswith("env-trend") and "co2" in k for k in keys(r))


def test_every_hit_carries_its_source_and_auditable_evidence():
    h = by_key(run(hour(co2_mmhg=3.1)), "env-co2-1h")
    ev = h.as_evidence()
    assert ev["source_document"] == "NASA-STD-3001 Vol. 2 Rev F"
    assert ev["hrp_hazard"] == "hostile_closed_environments"
    assert ev["action_key"] == "check_ventilation_and_filters"
    assert {
        "parameter",
        "value",
        "unit",
        "operator",
        "threshold",
        "window_s",
        "band",
        "evidence_state",
        "source_requirement",
    } <= set(ev)


def test_missing_metrics_do_not_break_the_evaluation():
    only_co2 = {"co2_mmhg": flat(0.6)}
    assert run(only_co2).hits == []
    assert derive_series(only_co2).get("pio2") is None


def test_hits_are_sorted_from_the_most_severe():
    r = run(nominal(humidity_pct=82.0, temperature_c=26.0))
    sev = [h.severity for h in r.hits]
    order = {"critical": 0, "alert": 1, "attention": 2}
    assert sev == sorted(sev, key=order.__getitem__)


def sampled(values: list[float], step: int) -> list[Sample]:
    n = len(values)
    return [Sample(NOW - timedelta(seconds=(n - 1 - i) * step), v) for i, v in enumerate(values)]


def test_a_trend_is_detected_with_the_normative_5_second_atmosphere_sampling():
    rng = random.Random(11)
    co2 = [0.7 + rng.gauss(0, 0.03) for _ in range(60)]  # 300 s at one sample every 5 s
    co2[-3:] = [v + 1.5 for v in co2[-3:]]  # rises in the last 15 s
    r = run({**nominal(seconds=300, step=5), "co2_mmhg": sampled(co2, 5)})
    assert "env-trend-co2" in keys(r)


def test_slow_temperature_sampling_every_minute_can_still_show_a_trend():
    rng = random.Random(5)
    t = [22.0 + rng.gauss(0, 0.05) for _ in range(40)]  # 40 min, one sample per minute
    t[-3:] = [v + 3.0 for v in t[-3:]]
    r = run({**nominal(seconds=2400, step=60), "temperature_c": sampled(t, 60)})
    assert "env-trend-t" in keys(r)


def test_an_exponential_leak_like_the_simulator_makes_triggers_the_rate_rule_within_10_seconds():
    # First 10 s of the leak: 46.3 kPa total drop with a constant of 0.05 per second.
    p = [
        Sample(NOW - timedelta(seconds=10 - i), 101.3 - 46.3 * (1 - 2.718281828 ** (-0.05 * i)))
        for i in range(11)
    ]
    r = run({**nominal(), "pressure_kpa": p})
    assert "env-dpdt" in keys(r)
    assert by_key(r, "env-dpdt").value > 13.5


def test_a_leak_that_has_already_slowed_down_is_exempt_by_the_one_psi_rule():
    # Around second 30 the drop over the last 10 s is 0.97 psi: it does not exceed 1.0 psi.
    p = [
        Sample(
            NOW - timedelta(seconds=10 - i), 101.3 - 46.3 * (1 - 2.718281828 ** (-0.05 * (20 + i)))
        )
        for i in range(11)
    ]
    assert "env-dpdt" not in keys(run({**nominal(), "pressure_kpa": p}))
