"""Alerta → recomendación sobre el outbox real de PostgreSQL (relay de Dev A, sin simulación)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.knowledge.adapters.inbound.events import register_knowledge
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import HandleAlertRaised
from spaceapp.modules.knowledge.contracts import RecommendationReady
from spaceapp.modules.monitoring.contracts import AlertRaised
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork

pytestmark = pytest.mark.integration

CATALOG = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "demo_catalog.json"


def alert(rule_key: str) -> EventEnvelope:
    payload = AlertRaised(
        alert_id=uuid4(),
        zone_id=uuid4(),
        rule_key=rule_key,
        severity="alerta",
        evidence={"value": 3.4},
        cause_hint="AMBIENTE",
    )
    return EventEnvelope.from_payload(
        payload, aggregate_type="alert", aggregate_id=payload.alert_id, partition_key="habitat:h-1"
    )


def registry(repo: InMemoryRecommendations) -> SubscriptionRegistry:
    reg = SubscriptionRegistry()
    handler = HandleAlertRaised(
        source=DemoKnowledgeSource.from_file(CATALOG), recommendations=repo, inbox=InMemoryInbox()
    )
    register_knowledge(reg, handler)
    return reg


async def outbox(sf) -> list[dict]:  # type: ignore[no-untyped-def]
    async with sf() as s:
        sql = "SELECT type, status, attempts, last_error, payload FROM platform.outbox_event ORDER BY id"
        return [dict(r) for r in (await s.execute(text(sql))).mappings().all()]


async def test_a_raised_alert_leaves_a_recommendation_ready_event_in_the_outbox(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    repo = InMemoryRecommendations()
    cause = alert("env-pio2-low")
    async with UnitOfWork(session_factory) as uow:
        await uow.publish(cause)
    relay = OutboxRelay(session_factory, registry(repo))

    await relay.run_once()  # entrega la alerta; el handler publica la recomendación
    await relay.run_once()  # entrega la recomendación (nadie la consume todavía)

    rows = await outbox(session_factory)
    assert [(r["type"], r["status"]) for r in rows] == [
        ("monitoring.alert_raised", "done"),
        ("knowledge.recommendation_ready", "done"),
    ]
    payload = rows[1]["payload"]
    payload = json.loads(payload) if isinstance(payload, str) else payload
    ready = RecommendationReady.model_validate(payload)
    assert ready.alert_id == cause.aggregate_id
    assert "revisar_suministro_o2_y_presion" in ready.action_keys
    assert {c.evidence_state for c in ready.citations} <= {"VERIFICADO"}
    assert len(repo.all()) == 1


async def test_an_alert_of_an_unknown_rule_stays_pending_with_the_error_recorded(
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    async with UnitOfWork(session_factory) as uow:
        await uow.publish(alert("regla-que-no-existe"))

    await OutboxRelay(session_factory, registry(InMemoryRecommendations())).run_once()

    [row] = await outbox(session_factory)
    assert row["status"] == "pending"
    assert row["attempts"] == 1
    assert "regla-que-no-existe" in row["last_error"]
