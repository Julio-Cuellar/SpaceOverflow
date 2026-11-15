from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import (
    HandleAlertRaised,
    HandleResult,
)
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.knowledge.domain.model import EvidenceState, UnknownRuleError
from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope


class CollectingContext:
    """Handler context that stores what was published, like the in-memory bus but without delivery."""

    def __init__(self) -> None:
        self.published: list[EventEnvelope] = []

    async def publish(self, event: EventEnvelope) -> None:
        self.published.append(event)

    @property
    def ctx(self) -> HandlerContext:
        return HandlerContext(publish=self.publish)

    def recommendations(self) -> list[RecommendationReady]:
        return [e.payload_as(RecommendationReady) for e in self.published]


def build(source: DemoKnowledgeSource):  # type: ignore[no-untyped-def]
    repo = InMemoryRecommendations()
    handler = HandleAlertRaised(source=source, recommendations=repo, inbox=InMemoryInbox())
    return handler, repo, CollectingContext()


def alert(rule_key: str = "env-co2-1h") -> EventEnvelope:
    """The event as Monitoring (dev A) publishes it: envelope partitioned by habitat."""
    payload = AlertRaised(
        alert_id=uuid.uuid4(),
        zone_id=None,
        rule_key=rule_key,
        severity="alert",
        evidence={"ppco2_1h_mmhg": 3.4},
        cause_hint="ENVIRONMENT",
    )
    return EventEnvelope.from_payload(
        payload,
        aggregate_type="alert",
        aggregate_id=payload.alert_id,
        partition_key="habitat:h-1",
    )


async def test_co2_alert_gets_at_least_two_actions(demo_source: DemoKnowledgeSource) -> None:
    handler, repo, c = build(demo_source)

    await handler.handle(alert("env-co2-1h"), c.ctx)

    [recommendation] = repo.all()
    assert len(recommendation.actions) >= 2


async def test_co2_alert_gets_a_citation_with_document_requirement_and_evidence_state(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)

    await handler.handle(alert("env-co2-1h"), c.ctx)

    [citation] = repo.all()[0].citations
    assert citation.document_code == "NASA-STD-3001 Vol. 2 Rev F"
    assert citation.requirement_ref == "V2 6004"
    assert citation.evidence_state is EvidenceState.VERIFIED


async def test_recommendation_is_labelled_as_demo_and_says_it_is_not_from_nasa(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)

    await handler.handle(alert("env-co2-1h"), c.ctx)

    recommendation = repo.all()[0]
    assert recommendation.source_kind == "DEMO"
    assert "demonstration data, not NASA data" in recommendation.body


async def test_publishes_recommendation_ready_with_action_keys_and_citations(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)

    await handler.handle(alert("env-co2-1h"), c.ctx)

    [event] = c.recommendations()
    recommendation = repo.all()[0]
    assert event.recommendation_id == recommendation.id
    assert event.action_keys == [action.key for action in recommendation.actions]
    assert len(event.citations) == len(recommendation.citations)


async def test_same_event_delivered_twice_does_not_duplicate_the_recommendation(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)
    event = alert("env-co2-1h")

    first = await handler.process(event, c.ctx)
    second = await handler.process(event, c.ctx)

    assert first is HandleResult.RECORDED
    assert second is HandleResult.DUPLICATE
    assert len(repo.all()) == 1
    assert len(c.published) == 1


async def test_unknown_rule_raises_and_leaves_the_event_unprocessed(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)
    event = alert("rule-that-does-not-exist")

    with pytest.raises(UnknownRuleError):
        await handler.handle(event, c.ctx)

    assert repo.all() == []
    # The event is still unmarked: a relay retry can process it later.
    assert handler.inbox_has(event.event_id) is False


async def test_the_published_event_continues_the_trace_of_the_alert(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, c = build(demo_source)
    cause = alert("env-co2-1h")

    await handler.handle(cause, c.ctx)

    [published] = c.published
    assert published.type == "knowledge.recommendation_ready"
    assert published.aggregate_type == "recommendation"
    assert published.aggregate_id == repo.all()[0].id
    # Same partition as the alert (habitat) and the causal chain stays linked.
    assert published.partition_key == cause.partition_key
    assert published.causation_id == cause.event_id
    assert published.correlation_id == cause.event_id


async def test_the_correlation_of_the_alert_is_kept_when_it_already_has_one(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, _, c = build(demo_source)
    cause = alert("env-co2-1h").model_copy(update={"correlation_id": uuid.uuid4()})

    await handler.handle(cause, c.ctx)

    assert c.published[0].correlation_id == cause.correlation_id


async def test_an_event_of_another_type_is_rejected(demo_source: DemoKnowledgeSource) -> None:
    handler, _, c = build(demo_source)
    other = alert("env-co2-1h").model_copy(update={"type": "monitoring.alert_resolved"})

    with pytest.raises(ValueError, match="alert_resolved"):
        await handler.handle(other, c.ctx)
    assert c.published == []


DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
RULE_KEYS = DemoKnowledgeSource.from_file(DEMO_CATALOG).rule_keys()


@pytest.mark.parametrize("rule_key", RULE_KEYS)
async def test_every_rule_in_the_catalog_gets_a_recommendation(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    handler, repo, c = build(demo_source)

    await handler.handle(alert(rule_key), c.ctx)

    [recommendation] = repo.all()
    assert recommendation.rule_key == rule_key
    assert recommendation.actions
    assert recommendation.citations
