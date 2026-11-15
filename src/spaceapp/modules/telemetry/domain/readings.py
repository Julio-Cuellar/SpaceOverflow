from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

MAX_BATCH = 500


class InvalidBatch(ValueError):
    pass


@dataclass(frozen=True)
class ReadingIn:
    sensor_id: UUID
    ts: datetime
    value: float
    quality: str = "ok"


@dataclass(frozen=True)
class SensorInfo:
    id: UUID
    habitat_id: UUID
    zone_id: UUID | None
    crew_member_id: UUID | None
    domain: str
    metric: str
    unit: str
    sample_period_s: int
    origin: str


def validate_batch(readings: Sequence[ReadingIn]) -> None:
    if not readings:
        raise InvalidBatch("el lote está vacío")
    if len(readings) > MAX_BATCH:
        raise InvalidBatch(
            f"un lote admite como máximo {MAX_BATCH} lecturas, llegaron {len(readings)}"
        )
    for r in readings:
        if r.ts.tzinfo is None or r.ts.utcoffset() is None:
            raise InvalidBatch(f"marca de tiempo sin zona horaria: {r.ts.isoformat()}")
        if not math.isfinite(r.value):
            raise InvalidBatch(f"el valor debe ser un número finito: {r.value}")
