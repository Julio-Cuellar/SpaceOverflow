import re
from typing import Any

import pytest
from pydantic import ValidationError

from spaceapp.event_registry import EVENT_MODELS

EXPECTED = {
    "telemetry.readings_recorded",
    "telemetry.scenario_changed",
    "monitoring.alert_raised",
    "monitoring.alert_acknowledged",
    "monitoring.alert_resolved",
    "knowledge.recommendation_ready",
    "knowledge.recommendation_enriched",
    "engagement.task_assigned",
    "engagement.task_completed",
    "engagement.task_created",
    "engagement.task_blocked",
    "engagement.ground_plan_applied",
    "assistant.answer_ready",
    "crew.baseline_updated",
    "crew.consent_changed",
    "groundlink.link_state_changed",
    "groundlink.batch_acknowledged",
    "groundlink.ground_plan_received",
    "facility.incident_opened",
    "facility.incident_updated",
    "facility.incident_resolved",
    "facility.zone_status_changed",
}

UUID1 = "00000000-0000-4000-8000-000000000001"
UUID2 = "00000000-0000-4000-8000-000000000002"
NOW = "2026-11-14T20:41:07+00:00"
CIT = {
    "document_code": "TB-004",
    "requirement_ref": None,
    "page": 3,
    "excerpt": "headache",
    "evidence_state": "TB",
}

SAMPLES: dict[str, dict[str, Any]] = {
    "telemetry.readings_recorded": {
        "batch_id": UUID1,
        "habitat_id": UUID2,
        "ts_from": NOW,
        "ts_to": NOW,
        "latest": [{"sensor_id": UUID1, "zone_id": UUID2, "metric": "co2", "value": 0.7}],
    },
    "telemetry.scenario_changed": {
        "key": "co2lab",
        "state": "started",
        "speed": 1.0,
        "zone_id": UUID1,
    },
    "monitoring.alert_raised": {
        "alert_id": UUID1,
        "zone_id": UUID2,
        "rule_key": "env-co2-1h",
        "severity": "alert",
        "evidence": {"value": 3.4},
        "cause_hint": "ENVIRONMENT",
    },
    "monitoring.alert_acknowledged": {"alert_id": UUID1, "crew_member_id": UUID2, "at": NOW},
    "monitoring.alert_resolved": {"alert_id": UUID1, "resolved_at": NOW, "duration_s": 120},
    "knowledge.recommendation_ready": {
        "alert_id": UUID1,
        "recommendation_id": UUID2,
        "action_keys": ["revisar_ventilacion"],
        "citations": [CIT],
    },
    "knowledge.recommendation_enriched": {"recommendation_id": UUID1, "text": "text"},
    "engagement.task_assigned": {
        "task_id": UUID1,
        "crew_member_id": UUID2,
        "kind": "INCIDENT",
        "origin": "SYSTEM",
        "action_key": None,
        "due_at": NOW,
    },
    "engagement.task_completed": {"task_id": UUID1, "action_key": None, "effective": True},
    "engagement.task_created": {
        "task_id": UUID1,
        "kind": "SHIP",
        "title": "Check filter",
        "zone_id": None,
        "origin": "CREW",
    },
    "engagement.task_blocked": {
        "task_id": UUID1,
        "origin": "GROUND",
        "reason": "Zone inaccessible",
    },
    "engagement.ground_plan_applied": {"plan_version": 12, "applied": [UUID1], "rejected": []},
    "assistant.answer_ready": {"utterance_id": UUID1, "text": "respuesta", "citations": [CIT]},
    "crew.baseline_updated": {"crew_member_id": UUID1, "metric": "hr", "value": 62.0},
    "crew.consent_changed": {"crew_member_id": UUID1, "category": "tasks", "shared": True},
    "groundlink.link_state_changed": {"state": "DOWN", "since": NOW, "queued": 3},
    "groundlink.batch_acknowledged": {"batch_id": UUID1, "items": 4, "acked_at": NOW},
    "groundlink.ground_plan_received": {
        "batch_id": UUID1,
        "plan_version": 12,
        "changes": [
            {
                "change": "NEW",
                "kind": "HEALTH",
                "title": "Record body mass",
                "recurrence": "Daily",
                "zone_code": None,
                "target_template_id": None,
            }
        ],
    },
    "facility.incident_opened": {
        "incident_id": UUID1,
        "zone_id": UUID2,
        "severity": "alert",
        "title": "High CO2",
        "description": "ppCO2 3.4",
        "source": "ALERT",
    },
    "facility.incident_updated": {
        "incident_id": UUID1,
        "severity": "critical",
        "status": "acknowledged",
        "note": None,
    },
    "facility.incident_resolved": {"incident_id": UUID1, "zone_id": UUID2, "resolved_at": NOW},
    "facility.zone_status_changed": {"zone_id": UUID1, "status": "alert", "open_incidents": 1},
}


def test_registry_has_exactly_the_agreed_events():
    assert set(EVENT_MODELS) == EXPECTED


def test_every_event_name_is_module_dot_fact():
    for name in EVENT_MODELS:
        assert re.fullmatch(r"[a-z]+\.[a-z_]+", name), name


def test_every_event_belongs_to_the_module_that_declares_it():
    for name, model in EVENT_MODELS.items():
        module = model.__module__.split(".")[2]  # spaceapp.modules.<module>.contracts
        assert name.split(".")[0] == module, (name, module)


def test_samples_cover_every_event():
    assert set(SAMPLES) == EXPECTED


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sample_payload_validates_against_its_model(name: str):
    model = EVENT_MODELS[name]
    assert model.event_type == name
    obj = model.model_validate(SAMPLES[name])
    assert model.model_validate(obj.model_dump(mode="json")) == obj


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_unknown_fields_are_rejected(name: str):
    with pytest.raises(ValidationError):
        EVENT_MODELS[name].model_validate({**SAMPLES[name], "invented_field": 1})


def test_severity_and_evidence_use_the_shared_vocabulary():
    bad = {**SAMPLES["monitoring.alert_raised"], "severity": "red"}
    with pytest.raises(ValidationError):
        EVENT_MODELS["monitoring.alert_raised"].model_validate(bad)
    bad_cit = {**CIT, "evidence_state": "INVENTED"}
    with pytest.raises(ValidationError):
        EVENT_MODELS["assistant.answer_ready"].model_validate(
            {**SAMPLES["assistant.answer_ready"], "citations": [bad_cit]}
        )


def test_the_realtime_gateway_only_subscribes_and_publishes_nothing():
    from spaceapp.modules.realtime.contracts import EVENTS

    assert EVENTS == {}
