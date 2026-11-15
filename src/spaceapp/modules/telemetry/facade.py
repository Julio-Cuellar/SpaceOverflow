"""Read-only queries that Telemetry exposes to other modules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class ReadingSample:
    ts: datetime
    value: float


class SqlReadingQuery:
    """Readings of a zone. Monitoring uses them to evaluate its rules."""

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
        """Window average weighted by the number of samples in each minute."""
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


@dataclass(frozen=True)
class LatestReadingView:
    zone_id: UUID | None
    metric: str
    unit: str
    domain: str
    origin: str
    value: float
    ts: datetime


@dataclass(frozen=True)
class SeriesPoint:
    ts: datetime
    avg: float
    min: float
    max: float


@dataclass(frozen=True)
class SeriesView:
    metric: str
    unit: str
    points: list[SeriesPoint]


RAW_LIMIT = 10_000


class TelemetryViews:
    """Readings for the interface: the latest value of each sensor and series per zone."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def latest(self, habitat_id: UUID) -> list[LatestReadingView]:
        sql = (
            "SELECT s.zone_id, s.metric, s.unit, s.domain, s.origin, r.value, r.ts "
            "FROM telemetry.sensor s CROSS JOIN LATERAL ("
            "  SELECT value, ts FROM telemetry.reading WHERE sensor_id = s.id "
            "  ORDER BY ts DESC LIMIT 1"
            ") r WHERE s.habitat_id = :h ORDER BY s.zone_id, s.metric"
        )
        async with self._sf() as session:
            rows = (await session.execute(text(sql), {"h": habitat_id})).all()
        return [LatestReadingView(*r) for r in rows]

    async def series(
        self,
        zone_id: UUID,
        metrics: Sequence[str],
        since: datetime,
        until: datetime,
        *,
        raw: bool = False,
    ) -> list[SeriesView]:
        """One series per metric with a sensor in the zone. Per minute (rollup) or raw."""
        if raw:
            points_sql = (
                "SELECT ts, value, value, value FROM telemetry.reading "
                "WHERE sensor_id = :s AND ts >= :a AND ts <= :b ORDER BY ts LIMIT :n"
            )
        else:
            points_sql = (
                "SELECT bucket, avg_v, min_v, max_v FROM telemetry.reading_rollup_1m "
                "WHERE sensor_id = :s AND bucket >= date_trunc('minute', CAST(:a AS timestamptz)) "
                "AND bucket <= :b ORDER BY bucket LIMIT :n"
            )
        async with self._sf() as session:
            sensors = (
                await session.execute(
                    text(
                        "SELECT id, metric, unit FROM telemetry.sensor "
                        "WHERE zone_id = :z AND metric = ANY(CAST(:m AS text[])) ORDER BY metric"
                    ),
                    {"z": zone_id, "m": list(metrics)},
                )
            ).all()
            out: list[SeriesView] = []
            for sensor_id, metric, unit in sensors:
                rows = await session.execute(
                    text(points_sql), {"s": sensor_id, "a": since, "b": until, "n": RAW_LIMIT}
                )
                out.append(SeriesView(metric, unit, [SeriesPoint(*r) for r in rows]))
        return out
