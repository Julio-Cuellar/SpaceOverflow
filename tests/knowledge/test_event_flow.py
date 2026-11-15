"""End-to-end walk over Dev A's bus: alert_raised comes in, recommendation_ready goes out."""

from __future__ import annotations

import contextlib
import uuid

from spaceapp.modules.knowledge.adapters.inbound.events import CONSUMER, register_knowledge
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import HandleAlertRaised
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.platform.bus import HandlerContext, InMemoryEventBus
from spaceapp.platform.events import EventEnvelope


def alert_envelope(rule_key: str) -> EventEnvelope:
    payload = AlertRaised(
        alert_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        rule_key=rule_key,
        severity="alert",
        evidence={"value": 3.4},
        cause_hint="ENVIRONMENT",
    )
    return EventEnvelope.from_payload(
        payload, aggregate_type="alert", aggregate_id=payload.alert_id, partition_key="habitat:h-1"
    )


def wire(source: DemoKnowledgeSource):  # type: ignore[no-untyped-def]
    bus = InMemoryEventBus()
    repo = InMemoryRecommendations()
    register_knowledge(
        bus, HandleAlertRaised(source=source, recommendations=repo, inbox=InMemoryInbox())
    )
    received: list[EventEnvelope] = []

    async def collect(event: EventEnvelope, ctx: HandlerContext) -> None:
        received.append(event)

    bus.subscribe("knowledge.recommendation_ready", "test.collector", collect)
    return bus, repo, received


async def test_an_alert_on_the_bus_produces_a_recommendation_with_citations(
    demo_source: DemoKnowledgeSource,
) -> None:
    bus, repo, received = wire(demo_source)
    alert = alert_envelope("env-co2-1h")

    await bus.publish(alert)

    [event] = received
    ready = event.payload_as(RecommendationReady)
    assert ready.alert_id == alert.aggregate_id
    assert ready.action_keys
    assert ready.citations[0].requirement_ref == "V2 6004"
    assert event.causation_id == alert.event_id
    assert len(repo.all()) == 1


async def test_the_same_alert_published_twice_gives_one_recommendation(
    demo_source: DemoKnowledgeSource,
) -> None:
    bus, repo, received = wire(demo_source)
    alert = alert_envelope("env-co2-1h")

    await bus.publish(alert)
    await bus.publish(alert)

    assert len(received) == 1
    assert len(repo.all()) == 1


async def test_an_alert_for_an_unknown_rule_fails_visibly_on_the_bus(
    demo_source: DemoKnowledgeSource,
) -> None:
    bus, repo, received = wire(demo_source)

    with contextlib.suppress(LookupError):
        await bus.publish(alert_envelope("rule-that-does-not-exist"))

    assert [consumer for consumer, _ in bus.failures] == [CONSUMER]
    assert received == []
    assert repo.all() == []


def test_the_consumer_name_follows_the_module_dot_handler_convention() -> None:
    assert CONSUMER == "knowledge.on_alert_raised"
