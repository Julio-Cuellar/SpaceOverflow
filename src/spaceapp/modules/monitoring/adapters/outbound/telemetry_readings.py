"""Readings for Monitoring, taken from the Telemetry facade."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.monitoring.domain.series import Sample
from spaceapp.modules.telemetry.facade import SqlReadingQuery


class TelemetryReadings:
    def __init__(self, session: AsyncSession) -> None:
        self._query = SqlReadingQuery(session)

    async def series(
        self, zone_id: UUID, metrics: Sequence[str], since: datetime, until: datetime
    ) -> dict[str, list[Sample]]:
        raw = await self._query.series(zone_id, metrics, since, until)
        return {m: [Sample(s.ts, s.value) for s in samples] for m, samples in raw.items()}
