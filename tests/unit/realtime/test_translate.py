"""Traducción de eventos del bus a mensajes del WebSocket (plan, sección 10.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from spaceapp.modules.knowledge.contracts import RecommendationEnriched, RecommendationReady
from spaceapp.modules.monitoring.contracts import AlertAcknowledged, AlertRaised, AlertResolved
from spaceapp.modules.realtime.domain.messages import TOPICS, translate
from spaceapp.modules.telemetry.contracts import LatestReading, ReadingsRecorded, ScenarioChanged
from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.vocab import Citation

ZONE = UUID("00000000-0000-4000-8000-0000000000aa")
NOW = datetime(2026, 11, 14, 20, 0, 0, tzinfo=UTC)


def env(payload: EventPayload, agg: str = "x") -> EventEnvelope:
    return EventEnvelope.from_payload(
        payload, aggregate_type=agg, aggregate_id=uuid4(), partition_key="p"
    )


def test_readings_recorded_becomes_one_tick_per_latest_reading() -> None:
    payload = ReadingsRecorded(
        batch_id=uuid4(),
        habitat_id=uuid4(),
        ts_from=NOW,
        ts_to=NOW,
        latest=[
            LatestReading(sensor_id=uuid4(), zone_id=ZONE, metric="co2", value=0.4),
            LatestReading(sensor_id=uuid4(), zone_id=None, metric="spo2", value=98.0),
        ],
    )
    event = env(payload)
    msgs = translate(event)
    assert [m.type for m in msgs] == ["telemetry.tick", "telemetry.tick"]
    assert all(m.topic == "telemetry" and m.seq is None for m in msgs)
    assert msgs[0].data == {
        "zone_id": str(ZONE),
        "sensor_id": msgs[0].data["sensor_id"],
        "metric": "co2",
        "value": 0.4,
        "ts": event.payload["ts_to"],
    }
    assert msgs[1].data["zone_id"] is None


def test_alert_raised_carries_severity_in_uppercase_and_the_evidence_state() -> None:
    alert_id = uuid4()
    payload = AlertRaised(
        alert_id=alert_id,
        zone_id=ZONE,
        rule_key="env-co2-1h",
        severity="alerta",
        evidence={"evidence_state": "VERIFICADO", "value": 0.9},
        cause_hint="AMBIENTE",
    )
    (msg,) = translate(env(payload))
    assert (msg.topic, msg.type) == ("alerts", "alert.raised")
    assert msg.data["alert_id"] == str(alert_id)
    assert msg.data["severity"] == "ALERTA"
    assert msg.data["evidence_state"] == "VERIFICADO"
    assert msg.data["rule_key"] == "env-co2-1h"
    assert msg.data["zone_id"] == str(ZONE)


def test_alert_lifecycle_events_map_to_updated_and_resolved() -> None:
    alert_id = uuid4()
    (ack,) = translate(env(AlertAcknowledged(alert_id=alert_id, crew_member_id=uuid4(), at=NOW)))
    assert (ack.topic, ack.type) == ("alerts", "alert.updated")
    assert ack.data["status"] == "acknowledged"
    (res,) = translate(env(AlertResolved(alert_id=alert_id, resolved_at=NOW, duration_s=42)))
    assert (res.topic, res.type) == ("alerts", "alert.resolved")
    assert res.data["duration_s"] == 42


def test_recommendation_events_go_to_the_alerts_topic() -> None:
    alert_id, rec_id = uuid4(), uuid4()
    cit = Citation(document_code="TB-004", excerpt="x", evidence_state="TB")
    (ready,) = translate(
        env(
            RecommendationReady(
                alert_id=alert_id, recommendation_id=rec_id, action_keys=["a"], citations=[cit]
            )
        )
    )
    assert (ready.topic, ready.type) == ("alerts", "recommendation.ready")
    assert ready.data["citations"][0]["document_code"] == "TB-004"
    (enr,) = translate(env(RecommendationEnriched(recommendation_id=rec_id, text="hola")))
    assert enr.type == "recommendation.enriched"


def test_scenario_changed_goes_to_telemetry() -> None:
    (msg,) = translate(env(ScenarioChanged(key="co2_slow", state="started", zone_id=ZONE)))
    assert (msg.topic, msg.type) == ("telemetry", "scenario.changed")
    assert msg.data["key"] == "co2_slow"


def test_events_without_a_ws_message_translate_to_nothing() -> None:
    other = EventEnvelope(
        type="crew.baseline_updated",
        aggregate_type="crew",
        aggregate_id=uuid4(),
        partition_key="p",
        payload={},
    )
    assert translate(other) == []


def test_every_translated_topic_is_a_known_topic() -> None:
    assert set(TOPICS) == {"telemetry", "alerts", "assistant", "habitat", "crew"}


def test_facility_events_reach_the_habitat_topic_in_upper_case() -> None:
    from spaceapp.modules.facility.contracts import IncidentOpened, ZoneStatusChanged

    zone, incident = uuid4(), uuid4()
    opened = EventEnvelope.from_payload(
        IncidentOpened(
            incident_id=incident,
            zone_id=zone,
            severity="alerta",
            title="CO₂ alto",
            description="d",
            source="ALERTA",
            code="INC-0007",
        ),
        aggregate_type="incident",
        aggregate_id=incident,
        partition_key="p",
    )
    [m] = translate(opened)
    assert (m.topic, m.type, m.data["severity"], m.data["status"], m.data["code"]) == (
        "habitat",
        "incident.opened",
        "ALERTA",
        "ABIERTA",
        "INC-0007",
    )
    changed = EventEnvelope.from_payload(
        ZoneStatusChanged(zone_id=zone, status="critico", open_incidents=2),
        aggregate_type="zone",
        aggregate_id=zone,
        partition_key="p",
    )
    [z] = translate(changed)
    assert (z.topic, z.type, z.data["status"], z.data["open_incidents"]) == (
        "habitat",
        "zone.status",
        "CRITICO",
        2,
    )
