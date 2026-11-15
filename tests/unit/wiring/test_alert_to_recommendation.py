"""El composition root suscribe Conocimiento (handler de Dev B) a las alertas de Monitoreo.

El caso de uso y su adaptador al bus los prueba Dev B en `tests/knowledge/` y en
`tests/integration/knowledge/`. Aquí solo se comprueba que `main.py` los conecta.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from spaceapp.main import build_knowledge, build_registry
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.platform.bus import HandlerContext, InMemoryEventBus
from spaceapp.platform.config import Settings
from spaceapp.platform.events import EventEnvelope

ZONE = UUID("00000000-0000-4000-8000-0000000000aa")


def alert(rule_key: str = "env-co2-1h") -> EventEnvelope:
    alert_id = uuid4()
    return EventEnvelope.from_payload(
        AlertRaised(
            alert_id=alert_id,
            zone_id=ZONE,
            rule_key=rule_key,
            severity="alerta",
            evidence={"value": 0.9},
            cause_hint="AMBIENTE",
        ),
        aggregate_type="alert",
        aggregate_id=alert_id,
        partition_key=str(ZONE),
    )


def test_the_composition_root_subscribes_knowledge_to_alerts() -> None:
    settings = Settings()
    registry = build_registry(settings, load_catalog(settings.rules_path))
    consumers = [s.consumer for s in registry.subscribers_for("monitoring.alert_raised")]
    assert "knowledge.on_alert_raised" in consumers


async def test_every_monitoring_rule_produces_a_recommendation_through_the_wired_handler() -> None:
    settings = Settings()
    knowledge = build_knowledge(settings)
    bus = InMemoryEventBus()
    bus.subscribe("monitoring.alert_raised", "knowledge.on_alert_raised", knowledge.handler.handle)
    ready: list[EventEnvelope] = []

    async def capture(event: EventEnvelope, _: HandlerContext) -> None:
        ready.append(event)

    bus.subscribe("knowledge.recommendation_ready", "test.capture", capture)
    rules = load_catalog(settings.rules_path).rules
    for rule in rules:
        await bus.publish(alert(rule.key))
    assert bus.failures == []
    assert len(ready) == len(rules)
    assert all(e.payload_as(RecommendationReady).citations for e in ready)
