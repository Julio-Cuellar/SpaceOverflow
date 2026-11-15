"""Decisiones sobre tickets y color de zonas. Funciones puras."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

SEVERITY_ORDER = {"normal": 0, "atencion": 1, "alerta": 2, "critico": 3}
AlertDecision = Literal["ignore", "open", "escalate", "note"]
ResolveError = Literal["ALREADY_RESOLVED", "ACTIVE_ALERTS"]


@dataclass(frozen=True)
class OpenTicket:
    severity: str
    source: str
    status: str


def opens_ticket(severity: str) -> bool:
    """Solo Alerta o más abre ticket automático. La tendencia (Atención) no."""
    return SEVERITY_ORDER[severity] >= SEVERITY_ORDER["alerta"]


def worst(severities: Iterable[str]) -> str:
    return max(severities, key=SEVERITY_ORDER.__getitem__, default="normal")


def on_alert(ticket: OpenTicket | None, severity: str) -> AlertDecision:
    """Un ticket automático por zona: si ya existe se anota; si sube la severidad, se escala."""
    if not opens_ticket(severity):
        return "ignore"
    if ticket is None:
        return "open"
    return "escalate" if SEVERITY_ORDER[severity] > SEVERITY_ORDER[ticket.severity] else "note"


def zone_status(alert_severities: Iterable[str], ticket_severities: Iterable[str]) -> str:
    return worst([*alert_severities, *ticket_severities])


def resolve_check(source: str, status: str, *, active_alerts: int) -> ResolveError | None:
    if status == "resuelta":
        return "ALREADY_RESOLVED"
    if source == "ALERTA" and active_alerts > 0:
        return "ACTIVE_ALERTS"
    return None


def describe(type_name: str, zone_name: str, evidence: Mapping[str, Any]) -> str:
    """Qué pasa, dónde, con qué valor, contra qué límite y según qué fuente."""
    text = f"{type_name} en {zone_name}"
    if "parameter" not in evidence or "value" not in evidence:
        return text + "."
    text += f": {evidence['parameter']} = {evidence['value']} {evidence.get('unit', '')}".rstrip()
    if "operator" in evidence and "threshold" in evidence:
        window = f", ventana {evidence['window_s']} s" if evidence.get("window_s") else ""
        text += f" (límite {evidence['operator']} {evidence['threshold']}{window})"
    text += "."
    source = " ".join(
        str(evidence[k]) for k in ("source_document", "source_requirement") if evidence.get(k)
    )
    if source:
        state = f" [{evidence['evidence_state']}]" if evidence.get("evidence_state") else ""
        text += f" Fuente: {source}{state}."
    return text
