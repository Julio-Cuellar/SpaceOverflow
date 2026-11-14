"""Caso de uso: una alerta llega y se guarda una recomendación de plantilla con citas.

No espera a ningún modelo de lenguaje. Es idempotente por (consumidor, event_id).
"""

from __future__ import annotations

import uuid
from enum import Enum

from spaceapp.modules.knowledge.contracts import AlertRaised, CitationDTO, RecommendationReady
from spaceapp.modules.knowledge.domain.model import Recommendation
from spaceapp.modules.knowledge.ports import (
    EventPublisher,
    Inbox,
    KnowledgeSource,
    RecommendationRepository,
)

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
        publisher: EventPublisher,
    ) -> None:
        self._source = source
        self._recommendations = recommendations
        self._inbox = inbox
        self._publisher = publisher

    def inbox_has(self, event_id: uuid.UUID) -> bool:
        return self._inbox.is_marked(CONSUMER, event_id)

    def __call__(self, event: AlertRaised) -> HandleResult:
        # Primero la guía: si la regla no existe se lanza el error y el evento queda sin marcar.
        guidance = self._source.guidance_for(event.rule_key)

        if not self._inbox.mark_once(CONSUMER, event.event_id):
            return HandleResult.DUPLICATE

        recommendation = Recommendation(
            # Id determinista: la misma alerta y regla produce siempre el mismo id.
            id=uuid.uuid5(_NAMESPACE, f"{event.alert_id}:{event.rule_key}"),
            alert_id=event.alert_id,
            rule_key=event.rule_key,
            source_kind=guidance.source_kind,
            body=guidance.body,
            actions=guidance.actions,
            citations=guidance.citations,
        )
        self._recommendations.save(recommendation)
        self._publisher.publish(
            RecommendationReady(
                alert_id=event.alert_id,
                recommendation_id=recommendation.id,
                action_keys=[action.key for action in recommendation.actions],
                citations=[
                    CitationDTO(
                        document_code=c.document_code,
                        requirement_ref=c.requirement_ref,
                        page=c.page,
                        excerpt=c.excerpt,
                        evidence_state=c.evidence_state.value,
                    )
                    for c in recommendation.citations
                ],
            )
        )
        return HandleResult.RECORDED
