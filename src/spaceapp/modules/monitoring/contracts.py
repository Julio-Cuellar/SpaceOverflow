"""Public Monitoring events and rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Literal
from uuid import UUID

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Severity


class AlertRaised(EventPayload):
    event_type: ClassVar[str] = "monitoring.alert_raised"
    alert_id: UUID
    zone_id: UUID | None = None
    rule_key: str
    severity: Severity
    evidence: dict[str, Any]
    cause_hint: Literal["ENVIRONMENT", "BODY", "UNDETERMINED"] | None = None


class AlertAcknowledged(EventPayload):
    event_type: ClassVar[str] = "monitoring.alert_acknowledged"
    alert_id: UUID
    crew_member_id: UUID
    at: datetime


class AlertResolved(EventPayload):
    event_type: ClassVar[str] = "monitoring.alert_resolved"
    alert_id: UUID
    resolved_at: datetime
    duration_s: int


EVENTS = {m.event_type: m for m in (AlertRaised, AlertAcknowledged, AlertResolved)}
