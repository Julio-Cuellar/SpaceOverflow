"""Esquema JSON de los mensajes de /ws. Se publica en contracts/ws-messages.schema.json."""

from __future__ import annotations

from typing import Any

from spaceapp.modules.realtime.domain.messages import SERVER_TYPES, SYSTEM_TYPES, TOPICS

_UUID = {"type": "string", "format": "uuid"}
_TIME = {"type": "string", "format": "date-time"}
_SEVERITY = {"enum": ["ATENCION", "ALERTA", "CRITICO"]}
_INCIDENT_STATUS = {"enum": ["ABIERTA", "RECONOCIDA", "RESUELTA"]}
_CITATION = {
    "type": "object",
    "required": ["document_code", "excerpt", "evidence_state"],
    "properties": {
        "document_code": {"type": "string"},
        "requirement_ref": {"type": ["string", "null"]},
        "page": {"type": ["integer", "null"]},
        "excerpt": {"type": "string"},
        "evidence_state": {"enum": ["VERIFICADO", "TB", "DEMO", "NO_VERIFICADO"]},
    },
}


def _obj(required: list[str], **properties: Any) -> dict[str, Any]:
    return {"type": "object", "required": required, "properties": properties}


# `data` de cada tipo. Los campos que no se listan pueden venir (no se cierra el objeto).
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
        cause_hint={"enum": ["AMBIENTE", "CUERPO", "INDETERMINADO", None]},
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
        source={"enum": ["ALERTA", "MANUAL"]},
        status={"const": "ABIERTA"},
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
        status={"const": "RESUELTA"},
    ),
    "zone.status": _obj(
        ["zone_id", "status", "open_incidents"],
        zone_id=_UUID,
        status={"enum": ["NORMAL", "ATENCION", "ALERTA", "CRITICO"]},
        open_incidents={"type": "integer", "minimum": 0},
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
        "title": "Mensajes de /ws",
        "description": (
            "Un solo canal de push. El servidor envía ServerMessage; el cliente, ClientMessage. "
            "`seq` es el id del outbox cuando el mensaje nace de un evento (se reenvía con "
            "`resume`); es null en los ticks y en el topic `system`. Con la cola llena se "
            "descartan ticks, nunca alertas. Sin mensajes durante 15 s el servidor envía `ping`."
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
