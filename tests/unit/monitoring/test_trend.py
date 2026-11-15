import random
from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from spaceapp.modules.monitoring.domain.series import Sample
from spaceapp.modules.monitoring.domain.trend import detect_trend

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def make(values: list[float], step: int = 1) -> list[Sample]:
    n = len(values)
    return [Sample(NOW - timedelta(seconds=(n - 1 - i) * step), v) for i, v in enumerate(values)]


def noisy_flat(base: float, sigma: float, n: int = 100, seed: int = 7) -> list[float]:
    rng = random.Random(seed)
    return [base + rng.gauss(0, sigma) for _ in range(n)]


def test_normal_noise_does_not_trigger_a_trend():
    assert detect_trend(make(noisy_flat(0.7, 0.04)), NOW, min_delta=0.6) is None


@given(st.floats(0.2, 50), st.integers(1, 200))
@settings(max_examples=40, deadline=None)
def test_bounded_noise_never_triggers_below_the_minimum_change(base, seed):
    rng = random.Random(seed)
    values = [base + rng.uniform(-0.05, 0.05) for _ in range(100)]
    assert detect_trend(make(values), NOW, min_delta=0.6) is None


def test_a_sustained_drift_is_detected_with_its_numbers():
    values = noisy_flat(0.7, 0.04, 100)
    values[-8:] = [v + 1.5 for v in values[-8:]]  # sube en los últimos 8 s
    r = detect_trend(make(values), NOW, min_delta=0.6)
    assert r is not None
    assert r.delta > 1.0 and r.recent_mean > r.baseline_mean
    assert r.threshold >= 0.6


def test_a_drop_is_also_a_trend():
    values = noisy_flat(21.0, 0.05, 100)
    values[-6:] = [v - 3 for v in values[-6:]]
    r = detect_trend(make(values), NOW, min_delta=1.0)
    assert r is not None and r.delta < 0


def test_a_single_spike_inside_the_baseline_does_not_count():
    values = noisy_flat(0.7, 0.04, 100)
    values[50] += 5  # dentro de la línea base (de -60 a -20 s)
    assert detect_trend(make(values), NOW, min_delta=0.6) is None


def test_without_enough_history_nothing_is_decided():
    assert detect_trend(make([1.0] * 10), NOW, min_delta=0.6) is None
    assert detect_trend([], NOW, min_delta=0.6) is None


def test_without_recent_samples_nothing_is_decided():
    old = make(noisy_flat(0.7, 0.04, 100))[:-10]  # faltan los últimos 10 s
    assert detect_trend(old, NOW, min_delta=0.6) is None
