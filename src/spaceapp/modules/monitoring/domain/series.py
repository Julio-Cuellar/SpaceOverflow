from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Sample:
    ts: datetime
    value: float


def within(samples: Sequence[Sample], start: datetime, end: datetime) -> list[Sample]:
    """Muestras con start <= ts <= end, en orden cronológico."""
    return sorted((s for s in samples if start <= s.ts <= end), key=lambda s: s.ts)


def mean(samples: Sequence[Sample]) -> float | None:
    if not samples:
        return None
    return sum(s.value for s in samples) / len(samples)


def latest(samples: Sequence[Sample]) -> Sample | None:
    return max(samples, key=lambda s: s.ts, default=None)
