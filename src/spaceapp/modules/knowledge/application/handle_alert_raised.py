"""Use case: an alert arrives and a template recommendation with citations is stored.

It waits for no language model. It is idempotent per (consumer, event_id): the platform's bus and
outbox already deliver each event once per consumer, and this use case reinforces it because an
unknown rule must leave the event unmarked so that it is retried.
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


def build_recommendation(
    source: KnowledgeSource, alert_id: uuid.UUID, rule_key: str
) -> Recommendation:
    """The recommendation of an alert. It is a pure function of the alert and the rule.

    The id is deterministic, so it can be rebuilt after a restart without storing it.
    """
    guidance = source.guidance_for(rule_key)
    return Recommendation(
        id=uuid.uuid5(_NAMESPACE, f"{alert_id}:{rule_key}"),
        alert_id=alert_id,
        rule_key=rule_key,
        source_kind=guidance.source_kind,
        body=guidance.body,
        actions=guidance.actions,
        citations=guidance.citations,
    )


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
        """Signature required by the bus: it returns nothing."""
        await self.process(event, ctx)

    async def process(self, event: EventEnvelope, ctx: HandlerContext) -> HandleResult:
        alert = event.payload_as(AlertRaised)
        # The guidance first: if the rule does not exist the error is raised and the event stays
        # unmarked.
        recommendation = build_recommendation(self._source, alert.alert_id, alert.rule_key)

        if not self._inbox.mark_once(CONSUMER, event.event_id):
            return HandleResult.DUPLICATE

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
                # Same partition as the alert, so the recommendation arrives after it.
                partition_key=event.partition_key,
                correlation_id=event.correlation_id or event.event_id,
                causation_id=event.event_id,
            )
        )
        return HandleResult.RECORDED
