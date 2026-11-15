"""Mantiene reading_rollup_1m. Se recalcula el rango del lote, así que es idempotente."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.telemetry.contracts import ReadingsRecorded
from spaceapp.modules.telemetry.ports.repositories import TelemetryRepository
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope


class RecomputeRollup:
    def __init__(self, repository: Callable[[AsyncSession], TelemetryRepository]) -> None:
        self._repository = repository

    async def handle(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        if ctx.session is None:  # bus en memoria: no hay base de datos que resumir
            return
        payload = event.payload_as(ReadingsRecorded)
        await self._repository(ctx.session).recompute_rollup(payload.ts_from, payload.ts_to)
