"""Eventos públicos de Nave e incidencias."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Severity

IncidentStatus = Literal["abierta", "reconocida", "resuelta"]
ZoneStatus = Literal["normal", "atencion", "alerta", "critico"]


class IncidentOpened(EventPayload):
    event_type: ClassVar[str] = "facility.incident_opened"
    incident_id: UUID
    zone_id: UUID
    severity: Severity
    title: str
    description: str
    source: Literal["ALERTA", "MANUAL"]


class IncidentUpdated(EventPayload):
    event_type: ClassVar[str] = "facility.incident_updated"
    incident_id: UUID
    severity: Severity
    status: IncidentStatus
    note: str | None = None


class IncidentResolved(EventPayload):
    event_type: ClassVar[str] = "facility.incident_resolved"
    incident_id: UUID
    zone_id: UUID
    resolved_at: datetime


class ZoneStatusChanged(EventPayload):
    event_type: ClassVar[str] = "facility.zone_status_changed"
    zone_id: UUID
    status: ZoneStatus
    open_incidents: int


EVENTS = {
    m.event_type: m for m in (IncidentOpened, IncidentUpdated, IncidentResolved, ZoneStatusChanged)
}
