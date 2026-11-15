"""Caso de uso: evaluar las reglas con cada lote de lecturas y gestionar las alertas."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.monitoring.contracts import AlertRaised, AlertResolved
from spaceapp.modules.monitoring.domain.engine import RuleHit, evaluate
from spaceapp.modules.monitoring.domain.lifecycle import reconcile
from spaceapp.modules.monitoring.domain.rules import RuleCatalog
from spaceapp.modules.monitoring.ports.repositories import AlertRepository, ReadingQuery
from spaceapp.modules.telemetry.contracts import ReadingsRecorded
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope, EventPayload

METRICS = ("pressure_kpa", "o2_pct", "co2_mmhg", "temperature_c", "humidity_pct")
TREND_BASELINE_S = 90  # historia que necesita el detector de tendencia


class EvaluateReadings:
    def __init__(
        self,
        catalog: RuleCatalog,
        readings: Callable[[AsyncSession | None], ReadingQuery],
        repository: Callable[[AsyncSession | None], AlertRepository],
        *,
        window_scale: float = 1.0,
        hysteresis: int = 3,
    ) -> None:
        self._catalog = catalog
        self._readings = readings
        self._repository = repository
        self._scale = window_scale
        self._hysteresis = hysteresis

    def _lookback(self) -> timedelta:
        """Historia necesaria: la mayor ventana (escalada) o la línea base de una tendencia."""
        spans = [
            float(r.params.get("baseline_from_s", TREND_BASELINE_S))
            if r.kind == "tendencia"
            else r.window_s * (self._scale if r.params.get("scalable", True) else 1.0)
            for r in self._catalog.active_rules()
        ]
        return timedelta(seconds=max(spans, default=0) + 5)

    async def handle(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        payload = event.payload_as(ReadingsRecorded)
        repo, readings = self._repository(ctx.session), self._readings(ctx.session)
        await repo.ensure_rules(self._catalog)
        now = payload.ts_to
        zones = sorted({r.zone_id for r in payload.latest if r.zone_id is not None}, key=str)
        for zone in zones:
            raw = await readings.series(zone, METRICS, now - self._lookback(), now)
            result = evaluate(
                zone, raw, self._catalog.active_rules(), now, window_scale=self._scale
            )
            active = await repo.active_for_zone(payload.habitat_id, zone)
            decision = reconcile(
                active, result.hits, superseded=result.superseded, hysteresis=self._hysteresis
            )
            for hit in decision.raise_hits:
                alert_id = await repo.add(payload.habitat_id, zone, hit, now)
                await self._publish(
                    ctx, event, payload.habitat_id, alert_id, _raised(alert_id, zone, hit)
                )
            for alert, hit in decision.keep:
                await repo.touch(alert.id, hit.as_evidence())
            for alert, streak in decision.clearing:
                await repo.set_streak(alert.id, streak)
            for alert in decision.resolve:
                duration = await repo.resolve(alert.id, now)
                resolved = AlertResolved(alert_id=alert.id, resolved_at=now, duration_s=duration)
                await self._publish(ctx, event, payload.habitat_id, alert.id, resolved)

    @staticmethod
    async def _publish(
        ctx: HandlerContext,
        cause: EventEnvelope,
        habitat_id: UUID,
        alert_id: UUID,
        payload: EventPayload,
    ) -> None:
        await ctx.publish(
            EventEnvelope.from_payload(
                payload,
                aggregate_type="alert",
                aggregate_id=alert_id,
                partition_key=f"habitat:{habitat_id}",
                correlation_id=cause.correlation_id or cause.event_id,
                causation_id=cause.event_id,
            )
        )


def _raised(alert_id: UUID, zone: UUID, hit: RuleHit) -> AlertRaised:
    # Todas las reglas actuales son ambientales: la causa probable es el aire.
    return AlertRaised(
        alert_id=alert_id,
        zone_id=zone,
        rule_key=hit.rule_key,
        severity=hit.severity,
        evidence=hit.as_evidence(),
        cause_hint="AMBIENTE",
    )
