"""JSON schema of the /ws messages. Published in contracts/ws-messages.schema.json."""

from __future__ import annotations

from typing import Any

from spaceapp.modules.realtime.domain.messages import SERVER_TYPES, SYSTEM_TYPES, TOPICS

_UUID = {"type": "string", "format": "uuid"}
_TIME = {"type": "string", "format": "date-time"}
_SEVERITY = {"enum": ["ATTENTION", "ALERT", "CRITICAL"]}
_INCIDENT_STATUS = {"enum": ["OPEN", "ACKNOWLEDGED", "RESOLVED"]}
_TASK_KIND = {"enum": ["HEALTH", "SHIP", "INCIDENT"]}
_TASK_ORIGIN = {"enum": ["GROUND", "SYSTEM", "CREW"]}
_CITATION = {
    "type": "object",
    "required": ["document_code", "excerpt", "evidence_state"],
    "properties": {
        "document_code": {"type": "string"},
        "requirement_ref": {"type": ["string", "null"]},
        "page": {"type": ["integer", "null"]},
        "excerpt": {"type": "string"},
        "evidence_state": {"enum": ["VERIFIED", "TB", "DEMO", "UNVERIFIED"]},
    },
}


def _obj(required: list[str], **properties: Any) -> dict[str, Any]:
    return {"type": "object", "required": required, "properties": properties}


# `data` of each type. Fields that are not listed may come (the object is not closed).
_DATA: dict[str, dict[str, Any]] = {
    "telemetry.tick": _obj(
        ["sensor_id", "metric", "value", "ts"],
        zone_id={"type": ["string", "null"], "format": "uuid"},
        sensor_id=_UUID,
        metric={"type": "string"},
        value={"type": "number"},
        ts=_TIME,
    ),
    "scenario.changed": _obj(
        ["key", "state"], key={"type": "string"}, state={"enum": ["started", "stopped"]}
    ),
    "alert.raised": _obj(
        ["alert_id", "rule_key", "severity"],
        alert_id=_UUID,
        zone_id={"type": ["string", "null"], "format": "uuid"},
        rule_key={"type": "string"},
        severity=_SEVERITY,
        cause_hint={"enum": ["ENVIRONMENT", "BODY", "UNDETERMINED", None]},
        evidence={"type": "object"},
    ),
    "alert.updated": _obj(
        ["alert_id", "status"], alert_id=_UUID, status={"const": "acknowledged"}, at=_TIME
    ),
    "alert.resolved": _obj(
        ["alert_id", "status"],
        alert_id=_UUID,
        status={"const": "resolved"},
        resolved_at=_TIME,
        duration_s={"type": "integer"},
    ),
    "recommendation.ready": _obj(
        ["alert_id", "recommendation_id", "action_keys", "citations", "composed_by"],
        alert_id=_UUID,
        recommendation_id=_UUID,
        action_keys={"type": "array", "items": {"type": "string"}},
        citations={"type": "array", "items": _CITATION},
        composed_by={"const": "template"},
    ),
    "recommendation.enriched": _obj(
        ["recommendation_id", "text", "composed_by"],
        recommendation_id=_UUID,
        text={"type": "string"},
        composed_by={"const": "llm"},
    ),
    "incident.opened": _obj(
        ["incident_id", "zone_id", "severity", "title", "description", "source", "status"],
        incident_id=_UUID,
        zone_id=_UUID,
        severity=_SEVERITY,
        title={"type": "string"},
        description={"type": "string"},
        source={"enum": ["ALERT", "MANUAL"]},
        code={"type": ["string", "null"], "description": "Human-readable ticket code, INC-0001"},
        status={"const": "OPEN"},
    ),
    "incident.updated": _obj(
        ["incident_id", "severity", "status"],
        incident_id=_UUID,
        severity=_SEVERITY,
        status=_INCIDENT_STATUS,
        note={"type": ["string", "null"]},
    ),
    "incident.resolved": _obj(
        ["incident_id", "zone_id", "resolved_at", "status"],
        incident_id=_UUID,
        zone_id=_UUID,
        resolved_at=_TIME,
        status={"const": "RESOLVED"},
    ),
    "zone.status": _obj(
        ["zone_id", "status", "open_incidents"],
        zone_id=_UUID,
        status={"enum": ["NORMAL", "ATTENTION", "ALERT", "CRITICAL"]},
        open_incidents={"type": "integer", "minimum": 0},
    ),
    "task.assigned": _obj(
        ["task_id", "crew_member_id", "kind", "origin", "due_at"],
        task_id=_UUID,
        crew_member_id=_UUID,
        kind=_TASK_KIND,
        origin=_TASK_ORIGIN,
        action_key={"type": ["string", "null"]},
        due_at=_TIME,
    ),
    "task.created": _obj(
        ["task_id", "kind", "title", "origin"],
        task_id=_UUID,
        kind=_TASK_KIND,
        title={"type": "string"},
        zone_id={"type": ["string", "null"], "format": "uuid"},
        origin=_TASK_ORIGIN,
    ),
    "task.completed": _obj(
        ["task_id"],
        task_id=_UUID,
        action_key={"type": ["string", "null"]},
        effective={"type": ["boolean", "null"]},
    ),
    "task.blocked": _obj(
        ["task_id", "origin", "reason"],
        task_id=_UUID,
        origin=_TASK_ORIGIN,
        reason={"type": "string"},
    ),
    "groundplan.received": _obj(
        ["batch_id", "plan_version", "changes"],
        batch_id=_UUID,
        plan_version={"type": "integer"},
        changes={"type": "array", "items": {"type": "object"}},
    ),
    "groundplan.applied": _obj(
        ["plan_version", "applied", "rejected"],
        plan_version={"type": "integer"},
        applied={"type": "array", "items": _UUID},
        rejected={
            "type": "array",
            "items": _obj(["title", "reason"], title={"type": "string"}, reason={"type": "string"}),
        },
    ),
    "groundplan.confirmed": _obj(
        ["batch_id", "items", "acked_at"], batch_id=_UUID, items={"type": "integer"}, acked_at=_TIME
    ),
    "groundlink.state": _obj(
        ["state", "since", "queued"],
        state={"enum": ["UP", "DOWN", "DEGRADED"]},
        since=_TIME,
        queued={"type": "integer", "minimum": 0},
    ),
    "assistant.answer": _obj(
        ["utterance_id", "text", "citations"],
        utterance_id=_UUID,
        text={"type": "string"},
        citations={"type": "array", "items": _CITATION},
    ),
}


def _client(kind: list[str], required: list[str], **properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["type", *required],
        "properties": {"type": {"enum": kind}, **properties},
    }


def ws_messages_schema() -> dict[str, Any]:
    server_types = [*SERVER_TYPES, *SYSTEM_TYPES]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "ws-messages.schema.json",
        "title": "/ws messages",
        "description": (
            "A single push channel. The server sends ServerMessage; the client, ClientMessage. "
            "`seq` is the outbox id when the message originates from an event (it is resent "
            "with `resume`); it is null on ticks and on the `system` topic. When the queue is "
            "full, ticks are dropped, never alerts. With no messages for 15 s the server sends "
            "`ping`."
        ),
        "$defs": {
            "ServerMessage": {
                "type": "object",
                "required": ["seq", "topic", "type", "at", "data"],
                "properties": {
                    "seq": {"type": ["integer", "null"]},
                    "topic": {"enum": [*TOPICS, "system"]},
                    "type": {"enum": server_types},
                    "at": _TIME,
                    "data": {"type": "object"},
                },
                "allOf": [
                    {
                        "if": {"properties": {"type": {"const": t}}},
                        "then": {"properties": {"topic": {"const": topic}, "data": _DATA[t]}},
                    }
                    for t, topic in SERVER_TYPES.items()
                ],
            },
            "ClientMessage": {
                "oneOf": [
                    _client(
                        ["subscribe", "unsubscribe"],
                        ["topics"],
                        topics={"type": "array", "items": {"enum": list(TOPICS)}},
                    ),
                    _client(["ping"], [], ts={}),
                    _client(
                        ["resume"],
                        ["after_outbox_id"],
                        after_outbox_id={"type": "integer", "minimum": 0},
                    ),
                ]
            },
        },
    }
