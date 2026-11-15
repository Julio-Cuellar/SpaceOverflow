"""The published /ws schema (contracts/ws-messages.schema.json) matches what is sent."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from spaceapp.modules.realtime.adapters.inbound.ws_schema import ws_messages_schema
from spaceapp.modules.realtime.domain.messages import (
    SERVER_TYPES,
    SYSTEM_TYPES,
    TOPICS,
    TRANSLATED_TYPES,
    translate,
)
from spaceapp.platform.events import EventEnvelope

T = datetime(2026, 11, 14, 20, 0, tzinfo=UTC).isoformat()
SAMPLES: dict[str, dict[str, Any]] = {
    "telemetry.readings_recorded": {
        "ts_to": T,
        "latest": [{"zone_id": None, "sensor_id": "s", "metric": "co2_mmhg", "value": 1.0}],
    },
    "telemetry.scenario_changed": {"key": "co2_slow", "state": "started"},
    "monitoring.alert_raised": {"alert_id": "a", "rule_key": "r", "severity": "alert"},
    "monitoring.alert_acknowledged": {"alert_id": "a", "crew_member_id": "c", "at": T},
    "monitoring.alert_resolved": {"alert_id": "a", "resolved_at": T, "duration_s": 3},
    "knowledge.recommendation_ready": {
        "alert_id": "a",
        "recommendation_id": "r",
        "action_keys": [],
        "citations": [],
    },
    "knowledge.recommendation_enriched": {"recommendation_id": "r", "text": "t"},
    "assistant.answer_ready": {"utterance_id": "u", "text": "t", "citations": []},
    "facility.incident_opened": {
        "incident_id": "i",
        "zone_id": "z",
        "severity": "alert",
        "title": "High CO₂",
        "description": "d",
        "source": "ALERT",
        "code": "INC-0001",
    },
    "facility.incident_updated": {"incident_id": "i", "severity": "critical", "status": "open"},
    "facility.incident_resolved": {"incident_id": "i", "zone_id": "z", "resolved_at": T},
    "facility.zone_status_changed": {"zone_id": "z", "status": "alert", "open_incidents": 1},
    "engagement.task_assigned": {
        "task_id": "t",
        "crew_member_id": "c",
        "kind": "HEALTH",
        "origin": "SYSTEM",
        "due_at": T,
    },
    "engagement.task_created": {
        "task_id": "t",
        "kind": "SHIP",
        "title": "x",
        "origin": "CREW",
    },
    "engagement.task_completed": {"task_id": "t", "effective": True},
    "engagement.task_blocked": {"task_id": "t", "origin": "GROUND", "reason": "r"},
    "engagement.ground_plan_applied": {"plan_version": 2, "applied": [], "rejected": []},
    "groundlink.ground_plan_received": {"batch_id": "b", "plan_version": 2, "changes": []},
    "groundlink.batch_acknowledged": {"batch_id": "b", "items": 1, "acked_at": T},
    "groundlink.link_state_changed": {"state": "DOWN", "since": T, "queued": 1},
}


def envelope(event_type: str) -> EventEnvelope:
    return EventEnvelope(
        type=event_type,
        aggregate_type="x",
        aggregate_id=uuid4(),
        partition_key="p",
        payload=SAMPLES[event_type],
    )


def test_every_translated_event_produces_a_published_type_on_its_topic() -> None:
    assert set(SAMPLES) == set(TRANSLATED_TYPES)
    for event_type in TRANSLATED_TYPES:
        messages = translate(envelope(event_type))
        assert messages, event_type
        for m in messages:
            assert SERVER_TYPES[m.type] == m.topic, m.type


def test_every_published_type_is_produced_by_some_event() -> None:
    produced = {m.type for t in TRANSLATED_TYPES for m in translate(envelope(t))}
    assert produced == set(SERVER_TYPES)


def test_the_schema_lists_every_topic_and_type() -> None:
    server = ws_messages_schema()["$defs"]["ServerMessage"]["properties"]
    assert set(server["topic"]["enum"]) == {*TOPICS, "system"}
    assert set(server["type"]["enum"]) == {*SERVER_TYPES, *SYSTEM_TYPES}


def test_the_client_messages_are_the_four_the_gateway_accepts() -> None:
    client = ws_messages_schema()["$defs"]["ClientMessage"]["oneOf"]
    kinds = {k for option in client for k in option["properties"]["type"]["enum"]}
    assert kinds == {"subscribe", "unsubscribe", "ping", "resume"}
