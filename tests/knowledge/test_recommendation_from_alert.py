from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
    ListPublisher,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import (
    HandleAlertRaised,
    HandleResult,
)
from spaceapp.modules.knowledge.contracts import AlertRaised
from spaceapp.modules.knowledge.domain.model import EvidenceState, UnknownRuleError


def build(source: DemoKnowledgeSource):  # type: ignore[no-untyped-def]
    repo = InMemoryRecommendations()
    inbox = InMemoryInbox()
    publisher = ListPublisher()
    handler = HandleAlertRaised(
        source=source, recommendations=repo, inbox=inbox, publisher=publisher
    )
    return handler, repo, publisher


def alert(rule_key: str = "env-co2-1h", event_id: uuid.UUID | None = None) -> AlertRaised:
    return AlertRaised(
        event_id=event_id or uuid.uuid4(),
        alert_id=uuid.uuid4(),
        zone_id=None,
        rule_key=rule_key,
        severity="ALERTA",
        evidence={"ppco2_1h_mmhg": 3.4},
        cause_hint="AMBIENTE",
    )


def test_co2_alert_gets_at_least_two_actions(demo_source: DemoKnowledgeSource) -> None:
    handler, repo, _ = build(demo_source)

    handler(alert("env-co2-1h"))

    [recommendation] = repo.all()
    assert len(recommendation.actions) >= 2


def test_co2_alert_gets_a_citation_with_document_requirement_and_evidence_state(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, _ = build(demo_source)

    handler(alert("env-co2-1h"))

    [citation] = repo.all()[0].citations
    assert citation.document_code == "NASA-STD-3001 Vol. 2 Rev F"
    assert citation.requirement_ref == "V2 6004"
    assert citation.evidence_state is EvidenceState.VERIFICADO


def test_recommendation_is_labelled_as_demo_and_says_it_is_not_from_nasa(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, _ = build(demo_source)

    handler(alert("env-co2-1h"))

    recommendation = repo.all()[0]
    assert recommendation.source_kind == "DEMO"
    assert "dato de demostración, no de NASA" in recommendation.body


def test_publishes_recommendation_ready_with_action_keys_and_citations(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, publisher = build(demo_source)

    handler(alert("env-co2-1h"))

    [event] = publisher.events
    recommendation = repo.all()[0]
    assert event.recommendation_id == recommendation.id
    assert event.action_keys == [action.key for action in recommendation.actions]
    assert len(event.citations) == len(recommendation.citations)


def test_same_event_delivered_twice_does_not_duplicate_the_recommendation(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, publisher = build(demo_source)
    event = alert("env-co2-1h")

    first = handler(event)
    second = handler(event)

    assert first is HandleResult.RECORDED
    assert second is HandleResult.DUPLICATE
    assert len(repo.all()) == 1
    assert len(publisher.events) == 1


def test_unknown_rule_raises_and_leaves_the_event_unprocessed(
    demo_source: DemoKnowledgeSource,
) -> None:
    handler, repo, _ = build(demo_source)
    event = alert("regla-que-no-existe")

    with pytest.raises(UnknownRuleError):
        handler(event)

    assert repo.all() == []
    # El evento sigue sin marcar: un reintento del relay puede procesarlo después.
    assert handler.inbox_has(event.event_id) is False


DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
RULE_KEYS = DemoKnowledgeSource.from_file(DEMO_CATALOG).rule_keys()


@pytest.mark.parametrize("rule_key", RULE_KEYS)
def test_every_rule_in_the_catalog_gets_a_recommendation(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    handler, repo, _ = build(demo_source)

    handler(alert(rule_key))

    [recommendation] = repo.all()
    assert recommendation.rule_key == rule_key
    assert recommendation.actions
    assert recommendation.citations
