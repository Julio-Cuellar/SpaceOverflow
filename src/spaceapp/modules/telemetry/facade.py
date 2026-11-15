"""Consultas de solo lectura que Telemetría expone a otros módulos."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ReadingSample:
    ts: datetime
    value: float


class SqlReadingQuery:
    """Lecturas de una zona. Las usa Monitoreo para evaluar sus reglas."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def series(
        self, zone_id: UUID, metrics: Sequence[str], since: datetime, until: datetime
    ) -> dict[str, list[ReadingSample]]:
        rows = await self._s.execute(
            text(
                "SELECT s.metric, r.ts, r.value FROM telemetry.reading r "
                "JOIN telemetry.sensor s ON s.id = r.sensor_id "
                "WHERE s.zone_id = :z AND s.metric = ANY(CAST(:m AS text[])) "
                "AND r.ts >= :a AND r.ts <= :b ORDER BY r.ts"
            ),
            {"z": zone_id, "m": list(metrics), "a": since, "b": until},
        )
        out: dict[str, list[ReadingSample]] = {m: [] for m in metrics}
        for metric, ts, value in rows:
            out[metric].append(ReadingSample(ts, value))
        return out

    async def rollup_mean(
        self, zone_id: UUID, metric: str, window_s: int, until: datetime
    ) -> float | None:
        """Promedio de la ventana ponderado por la cantidad de muestras de cada minuto."""
        value = (
            await self._s.execute(
                text(
                    "SELECT sum(u.avg_v * u.n) / NULLIF(sum(u.n), 0) "
                    "FROM telemetry.reading_rollup_1m u "
                    "JOIN telemetry.sensor s ON s.id = u.sensor_id "
                    "WHERE s.zone_id = :z AND s.metric = :m AND u.bucket >= :a AND u.bucket <= :b"
                ),
                {"z": zone_id, "m": metric, "a": until - timedelta(seconds=window_s), "b": until},
            )
        ).scalar_one()
        return float(value) if value is not None else None
