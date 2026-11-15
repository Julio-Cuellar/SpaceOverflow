"""Caso de uso: una alerta llega y se guarda una recomendación de plantilla con citas.

No espera a ningún modelo de lenguaje. Es idempotente por (consumidor, event_id): el bus y el
outbox de la plataforma ya entregan cada evento una vez por consumidor, y este caso de uso lo
refuerza porque una regla desconocida debe dejar el evento sin marcar para que se reintente.
"""

from __future__ import annotations

import uuid
from enum import Enum

from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.knowledge.domain.model import Recommendation
from spaceapp.modules.knowledge.ports import Inbox, KnowledgeSource, RecommendationRepository
from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.vocab import Citation

CONSUMER = "knowledge.on_alert_raised"
_NAMESPACE = uuid.NAMESPACE_URL


class HandleResult(Enum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"


class HandleAlertRaised:
    def __init__(
        self,
        *,
        source: KnowledgeSource,
        recommendations: RecommendationRepository,
        inbox: Inbox,
    ) -> None:
        self._source = source
        self._recommendations = recommendations
        self._inbox = inbox

    def inbox_has(self, event_id: uuid.UUID) -> bool:
        return self._inbox.is_marked(CONSUMER, event_id)

    async def handle(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        """Firma que exige el bus: no devuelve nada."""
        await self.process(event, ctx)

    async def process(self, event: EventEnvelope, ctx: HandlerContext) -> HandleResult:
        alert = event.payload_as(AlertRaised)
        # Primero la guía: si la regla no existe se lanza el error y el evento queda sin marcar.
        guidance = self._source.guidance_for(alert.rule_key)

        if not self._inbox.mark_once(CONSUMER, event.event_id):
            return HandleResult.DUPLICATE

        recommendation = Recommendation(
            # Id determinista: la misma alerta y regla produce siempre el mismo id.
            id=uuid.uuid5(_NAMESPACE, f"{alert.alert_id}:{alert.rule_key}"),
            alert_id=alert.alert_id,
            rule_key=alert.rule_key,
            source_kind=guidance.source_kind,
            body=guidance.body,
            actions=guidance.actions,
            citations=guidance.citations,
        )
        self._recommendations.save(recommendation)
        await ctx.publish(
            EventEnvelope.from_payload(
                RecommendationReady(
                    alert_id=alert.alert_id,
                    recommendation_id=recommendation.id,
                    action_keys=[action.key for action in recommendation.actions],
                    citations=[
                        Citation(
                            document_code=c.document_code,
                            requirement_ref=c.requirement_ref,
                            page=c.page,
                            excerpt=c.excerpt,
                            evidence_state=c.evidence_state.value,
                        )
                        for c in recommendation.citations
                    ],
                ),
                aggregate_type="recommendation",
                aggregate_id=recommendation.id,
                # Misma partición que la alerta, así la recomendación llega después de ella.
                partition_key=event.partition_key,
                correlation_id=event.correlation_id or event.event_id,
                causation_id=event.event_id,
            )
        )
        return HandleResult.RECORDED
