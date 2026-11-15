from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from spaceapp.modules.telemetry.domain.simulator import (
    SimReading,
    Simulator,
    UnknownScenario,
    UnknownZone,
    ZoneBaseline,
)

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
ZONES = [
    ZoneBaseline("lab", 22.6, 44.0, 0.7),
    ZoneBaseline("air", 21.5, 38.0, 0.4),
    ZoneBaseline("crew", 22.0, 43.0, 0.8),
]
METRICS = {"pressure_kpa", "o2_pct", "co2_mmhg", "temperature_c", "humidity_pct"}


def make(seed: int = 7, noise: bool = True) -> Simulator:
    return Simulator(ZONES, seed=seed, noise=noise)


def run(sim: Simulator, seconds: int, step: int = 1, start: int = 0) -> list[SimReading]:
    out: list[SimReading] = []
    for s in range(start, seconds + 1, step):
        out += sim.tick(T0 + timedelta(seconds=s))
    return out


def value_at(readings: list[SimReading], zone: str, metric: str, second: int) -> float:
    ts = T0 + timedelta(seconds=second)
    return next(r.value for r in readings if (r.zone_code, r.metric, r.ts) == (zone, metric, ts))


def test_the_first_tick_emits_every_metric_of_every_zone():
    first = make().tick(T0)
    assert len(first) == 3 * 5
    assert {r.metric for r in first} == METRICS


def test_each_metric_follows_the_sampling_period_of_the_norm():
    c = Counter((r.zone_code, r.metric) for r in run(make(), 120))
    assert c[("lab", "pressure_kpa")] == 121  # cada 1 s
    assert c[("lab", "o2_pct")] == c[("lab", "co2_mmhg")] == 25  # cada 5 s
    assert c[("lab", "temperature_c")] == c[("lab", "humidity_pct")] == 3  # cada 1 min


def test_the_simulation_is_deterministic_for_a_seed_and_differs_between_seeds():
    a, b, c = run(make(7), 30), run(make(7), 30), run(make(8), 30)
    assert a == b
    assert a != c


def test_nominal_values_stay_close_to_the_baseline():
    readings = run(make(), 120)
    for r in readings:
        if r.zone_code == "lab":
            limits = {
                "pressure_kpa": (101.3, 0.5),
                "o2_pct": (21.0, 0.5),
                "co2_mmhg": (0.7, 0.3),
                "temperature_c": (22.6, 0.8),
                "humidity_pct": (44.0, 3.0),
            }
            base, tol = limits[r.metric]
            assert abs(r.value - base) <= tol, (r.metric, r.value)


def test_a_slow_co2_scenario_only_affects_its_zone():
    sim = make()
    sim.start("co2_slow", "lab")
    readings = run(sim, 60)
    assert value_at(readings, "lab", "co2_mmhg", 60) > 3.0
    assert value_at(readings, "air", "co2_mmhg", 60) < 1.0


def test_a_pressure_leak_drops_fast_enough_to_break_the_rate_limit():
    sim = make()
    sim.start("pressure_leak", "air")
    readings = run(sim, 60)
    p0, p10 = (
        value_at(readings, "air", "pressure_kpa", 0),
        value_at(readings, "air", "pressure_kpa", 10),
    )
    assert (p0 - p10) / 6.89476 > 1.0  # más de 1 psi en 10 s
    assert value_at(readings, "air", "pressure_kpa", 60) < 70
    assert value_at(readings, "lab", "pressure_kpa", 60) > 100


@pytest.mark.parametrize(
    ("scenario", "metric", "check"),
    [
        ("humidity_high", "humidity_pct", lambda v: v > 75),
        ("o2_failure", "o2_pct", lambda v: v < 18.5),
        ("heat", "temperature_c", lambda v: v > 27),
    ],
)
def test_each_scenario_drives_its_parameter_out_of_range(scenario, metric, check):
    sim = make()
    sim.start(scenario, "lab")
    assert check(value_at(run(sim, 120), "lab", metric, 120))


def test_stopping_a_scenario_brings_the_zone_back_to_normal():
    sim = make()
    sim.start("co2_slow", "lab")
    run(sim, 60)
    sim.stop("co2_slow", "lab")
    readings = run(sim, 240, start=61)
    assert value_at(readings, "lab", "co2_mmhg", 240) < 1.0
    assert sim.active() == {}


def test_a_higher_speed_reaches_the_target_sooner():
    slow, fast = make(noise=False), make(noise=False)
    slow.start("co2_slow", "lab", speed=1.0)
    fast.start("co2_slow", "lab", speed=3.0)
    assert value_at(run(fast, 10), "lab", "co2_mmhg", 10) > value_at(
        run(slow, 10), "lab", "co2_mmhg", 10
    )


def test_the_dynamics_do_not_depend_on_the_tick_size():
    fine, coarse = make(noise=False), make(noise=False)
    fine.start("co2_slow", "lab")
    coarse.start("co2_slow", "lab")
    a = value_at(run(fine, 60, step=1), "lab", "co2_mmhg", 60)
    b = value_at(run(coarse, 60, step=5), "lab", "co2_mmhg", 60)
    assert a == pytest.approx(b, rel=1e-6)


def test_unknown_scenarios_and_zones_are_rejected_and_a_zone_is_required():
    sim = make()
    with pytest.raises(UnknownScenario):
        sim.start("terremoto", "lab")
    with pytest.raises(UnknownZone):
        sim.start("co2_slow", "narnia")
    with pytest.raises(ValueError, match="zona"):
        sim.start("co2_slow", None)


def test_active_lists_running_scenarios_by_zone():
    sim = make()
    sim.start("co2_slow", "lab")
    sim.start("heat", "lab")
    sim.start("humidity_high", "air", speed=2.0)
    assert sim.active() == {"lab": {"co2_slow": 1.0, "heat": 1.0}, "air": {"humidity_high": 2.0}}
