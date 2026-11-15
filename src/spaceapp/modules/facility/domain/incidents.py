"""Decisions about tickets and zone color. Pure functions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

SEVERITY_ORDER = {"normal": 0, "attention": 1, "alert": 2, "critical": 3}
AlertDecision = Literal["ignore", "open", "escalate", "note"]
ResolveError = Literal["ALREADY_RESOLVED", "ACTIVE_ALERTS"]


@dataclass(frozen=True)
class OpenTicket:
    severity: str
    source: str
    status: str


def incident_code(number: int) -> str:
    """Human-readable ticket code from its sequential number: INC-0001."""
    return f"INC-{number:04d}"


def opens_ticket(severity: str) -> bool:
    """Only Alert or higher opens an automatic ticket. The trend (Attention) does not."""
    return SEVERITY_ORDER[severity] >= SEVERITY_ORDER["alert"]


def worst(severities: Iterable[str]) -> str:
    return max(severities, key=SEVERITY_ORDER.__getitem__, default="normal")


def on_alert(ticket: OpenTicket | None, severity: str) -> AlertDecision:
    """One automatic ticket per zone: if it exists it is noted; if severity rises, escalated."""
    if not opens_ticket(severity):
        return "ignore"
    if ticket is None:
        return "open"
    return "escalate" if SEVERITY_ORDER[severity] > SEVERITY_ORDER[ticket.severity] else "note"


def zone_status(alert_severities: Iterable[str], ticket_severities: Iterable[str]) -> str:
    return worst([*alert_severities, *ticket_severities])


def resolve_check(source: str, status: str, *, active_alerts: int) -> ResolveError | None:
    if status == "resolved":
        return "ALREADY_RESOLVED"
    if source == "ALERT" and active_alerts > 0:
        return "ACTIVE_ALERTS"
    return None


def describe(type_name: str, zone_name: str, evidence: Mapping[str, Any]) -> str:
    """What happens, where, with what value, against what limit and per which source."""
    text = f"{type_name} in {zone_name}"
    if "parameter" not in evidence or "value" not in evidence:
        return text + "."
    text += f": {evidence['parameter']} = {evidence['value']} {evidence.get('unit', '')}".rstrip()
    if "operator" in evidence and "threshold" in evidence:
        window = f", window {evidence['window_s']} s" if evidence.get("window_s") else ""
        text += f" (limit {evidence['operator']} {evidence['threshold']}{window})"
    text += "."
    source = " ".join(
        str(evidence[k]) for k in ("source_document", "source_requirement") if evidence.get(k)
    )
    if source:
        state = f" [{evidence['evidence_state']}]" if evidence.get("evidence_state") else ""
        text += f" Source: {source}{state}."
    return text
