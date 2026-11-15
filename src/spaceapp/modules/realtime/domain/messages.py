"""Mensajes que el servidor empuja por `/ws` y su traducción desde los eventos del bus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spaceapp.platform.events import EventEnvelope

TOPICS = ("telemetry", "alerts", "assistant")

# Eventos que producen mensajes con `seq` (id del outbox) y se pueden reenviar con `resume`.
# Las lecturas no: son ticks sin `seq`, solo importa el último valor.
REPLAYABLE_TYPES = (
    "monitoring.alert_raised",
    "monitoring.alert_acknowledged",
    "monitoring.alert_resolved",
    "knowledge.recommendation_ready",
    "knowledge.recommendation_enriched",
    "assistant.answer_ready",
    "telemetry.scenario_changed",
)
TRANSLATED_TYPES = ("telemetry.readings_recorded", *REPLAYABLE_TYPES)

# Tipo de mensaje del servidor -> topic al que pertenece (contracts/ws-messages.schema.json).
SERVER_TYPES: dict[str, str] = {
    "telemetry.tick": "telemetry",
    "scenario.changed": "telemetry",
    "alert.raised": "alerts",
    "alert.updated": "alerts",
    "alert.resolved": "alerts",
    "recommendation.ready": "alerts",
    "recommendation.enriched": "alerts",
    "assistant.answer": "assistant",
}
# Respuestas del servidor en el topic `system`. No llevan `seq` ni se reenvían.
SYSTEM_TYPES = ("subscribed", "pong", "ping", "resumed", "error")


@dataclass(frozen=True)
class WsMessage:
    seq: int | None
    topic: str
    type: str
    at: str
    data: dict[str, Any]

    def with_seq(self, seq: int | None) -> WsMessage:
        return WsMessage(seq, self.topic, self.type, self.at, self.data)

    def as_json(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "topic": self.topic,
            "type": self.type,
            "at": self.at,
            "data": self.data,
        }


def system_message(type_: str, data: dict[str, Any], at: str) -> WsMessage:
    """Respuestas del servidor a lo que pide el cliente (subscribed, pong, resumed, error)."""
    return WsMessage(None, "system", type_, at, data)


def translate(event: EventEnvelope) -> list[WsMessage]:
    p = event.payload
    at = event.occurred_at.isoformat()

    def one(topic: str, type_: str, data: dict[str, Any]) -> list[WsMessage]:
        return [WsMessage(None, topic, type_, at, data)]

    match event.type:
        case "telemetry.readings_recorded":
            return [
                WsMessage(
                    None,
                    "telemetry",
                    "telemetry.tick",
                    at,
                    {
                        "zone_id": r.get("zone_id"),
                        "sensor_id": r["sensor_id"],
                        "metric": r["metric"],
                        "value": r["value"],
                        "ts": p["ts_to"],
                    },
                )
                for r in p["latest"]
            ]
        case "telemetry.scenario_changed":
            return one("telemetry", "scenario.changed", dict(p))
        case "monitoring.alert_raised":
            return one(
                "alerts",
                "alert.raised",
                {
                    "alert_id": p["alert_id"],
                    "zone_id": p.get("zone_id"),
                    "rule_key": p["rule_key"],
                    "severity": str(p["severity"]).upper(),
                    "evidence_state": p.get("evidence", {}).get("evidence_state"),
                    "cause_hint": p.get("cause_hint"),
                    "evidence": p.get("evidence", {}),
                },
            )
        case "monitoring.alert_acknowledged":
            return one("alerts", "alert.updated", {**p, "status": "acknowledged"})
        case "monitoring.alert_resolved":
            return one("alerts", "alert.resolved", {**p, "status": "resolved"})
        case "knowledge.recommendation_ready":
            return one("alerts", "recommendation.ready", {**p, "composed_by": "template"})
        case "knowledge.recommendation_enriched":
            return one("alerts", "recommendation.enriched", {**p, "composed_by": "llm"})
        case "assistant.answer_ready":
            return one("assistant", "assistant.answer", dict(p))
        case _:
            return []
