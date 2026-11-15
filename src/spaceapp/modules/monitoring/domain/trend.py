"""Trend anomaly detector. Demo rule (`DEMO`), deterministic."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import pstdev

from spaceapp.modules.monitoring.domain.series import Sample, mean, within


@dataclass(frozen=True)
class TrendResult:
    recent_mean: float
    baseline_mean: float
    baseline_std: float
    delta: float
    threshold: float


def detect_trend(
    samples: Sequence[Sample],
    now: datetime,
    *,
    min_delta: float,
    k: float = 4.0,
    baseline_from_s: int = 60,
    baseline_to_s: int = 20,
    recent_s: int = 5,
    min_baseline_points: int = 20,
    min_recent_points: int = 3,
) -> TrendResult | None:
    """Compares the recent mean with that of an earlier baseline.

    There is an anomaly if the change exceeds the larger of `k` deviations and `min_delta`.
    Without enough history nothing is decided.
    """
    base = within(
        samples, now - timedelta(seconds=baseline_from_s), now - timedelta(seconds=baseline_to_s)
    )
    recent = within(samples, now - timedelta(seconds=recent_s), now)
    if len(base) < min_baseline_points or len(recent) < min_recent_points:
        return None
    base_mean = mean(base)
    recent_mean = mean(recent)
    assert base_mean is not None and recent_mean is not None
    sd = pstdev(s.value for s in base)
    delta = recent_mean - base_mean
    threshold = max(k * sd, min_delta)
    if abs(delta) <= threshold:
        return None
    return TrendResult(recent_mean, base_mean, sd, delta, threshold)
