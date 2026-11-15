"""Repositorio de telemetría sobre PostgreSQL."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.telemetry.domain.readings import ReadingIn, SensorInfo


class SqlTelemetryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def register_sensors(self, sensors: Sequence[SensorInfo]) -> None:
        for s in sensors:
            await self._s.execute(
                text(
                    "INSERT INTO telemetry.sensor (id, habitat_id, zone_id, crew_member_id, domain, "
                    "metric, unit, sample_period_s, origin) VALUES (:id, :h, :z, :c, :d, :m, :u, :p, :o) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": s.id,
                    "h": s.habitat_id,
                    "z": s.zone_id,
                    "c": s.crew_member_id,
                    "d": s.domain,
                    "m": s.metric,
                    "u": s.unit,
                    "p": s.sample_period_s,
                    "o": s.origin,
                },
            )

    async def sensors_by_id(self, ids: Iterable[UUID]) -> dict[UUID, SensorInfo]:
        rows = await self._s.execute(
            text(
                "SELECT id, habitat_id, zone_id, crew_member_id, domain, metric, unit, "
                "sample_period_s, origin FROM telemetry.sensor WHERE id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": list(ids)},
        )
        return {r.id: SensorInfo(*r) for r in rows}

    async def ensure_partitions(self, days: Iterable[date]) -> None:
        for day in sorted(set(days)):
            await self._s.execute(text("SELECT telemetry.ensure_reading_partition(:d)"), {"d": day})

    async def insert_readings(self, readings: Sequence[ReadingIn]) -> list[tuple[UUID, datetime]]:
        rows = await self._s.execute(
            text(
                "INSERT INTO telemetry.reading (sensor_id, ts, value, quality) "
                "SELECT * FROM unnest(CAST(:s AS uuid[]), CAST(:t AS timestamptz[]), "
                "CAST(:v AS float8[]), CAST(:q AS text[])) ON CONFLICT DO NOTHING "
                "RETURNING sensor_id, ts"
            ),
            {
                "s": [r.sensor_id for r in readings],
                "t": [r.ts for r in readings],
                "v": [r.value for r in readings],
                "q": [r.quality for r in readings],
            },
        )
        return [(r.sensor_id, r.ts) for r in rows]

    async def recompute_rollup(self, ts_from: datetime, ts_to: datetime) -> None:
        await self._s.execute(
            text(
                "INSERT INTO telemetry.reading_rollup_1m (sensor_id, bucket, avg_v, min_v, max_v, n) "
                "SELECT sensor_id, date_trunc('minute', ts AT TIME ZONE 'UTC') AT TIME ZONE 'UTC', "
                "avg(value), min(value), max(value), count(*) FROM telemetry.reading "
                "WHERE ts >= (date_trunc('minute', CAST(:f AS timestamptz) AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') "
                "AND ts < (date_trunc('minute', CAST(:t AS timestamptz) AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') "
                "+ interval '1 minute' GROUP BY 1, 2 "
                "ON CONFLICT (sensor_id, bucket) DO UPDATE SET avg_v = EXCLUDED.avg_v, "
                "min_v = EXCLUDED.min_v, max_v = EXCLUDED.max_v, n = EXCLUDED.n"
            ),
            {"f": ts_from, "t": ts_to},
        )

    async def start_scenario(
        self, habitat_id: UUID, zone_id: UUID | None, key: str, speed: float, at: datetime
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO telemetry.scenario_run (id, habitat_id, zone_id, scenario_key, state, "
                "speed, started_at) VALUES (:id, :h, :z, :k, 'started', :sp, :t)"
            ),
            {"id": uuid4(), "h": habitat_id, "z": zone_id, "k": key, "sp": speed, "t": at},
        )

    async def stop_scenario(
        self, habitat_id: UUID, zone_id: UUID | None, key: str, at: datetime
    ) -> None:
        await self._s.execute(
            text(
                "UPDATE telemetry.scenario_run SET state = 'stopped', stopped_at = :t WHERE id IN ("
                "SELECT id FROM telemetry.scenario_run WHERE habitat_id = :h AND scenario_key = :k "
                "AND state = 'started' AND (CAST(:z AS uuid) IS NULL OR zone_id = CAST(:z AS uuid)))"
            ),
            {"t": at, "h": habitat_id, "z": zone_id, "k": key},
        )
