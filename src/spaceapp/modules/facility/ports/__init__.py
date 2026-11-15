"""Facility ports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from spaceapp.modules.facility.domain.plan import Plan


@dataclass(frozen=True)
class ZoneAlert:
    alert_id: UUID
    zone_id: UUID
    rule_key: str
    severity: str
    raised_at: datetime


@dataclass(frozen=True)
class TicketRow:
    id: UUID
    zone_id: UUID
    type_key: str
    source: str
    severity: str
    status: str


class ActiveAlertsSource(Protocol):
    """Active Monitoring alerts, to rebuild state at startup."""

    async def __call__(self, habitat_id: UUID) -> Sequence[ZoneAlert]: ...


class FacilityRepository(Protocol):
    async def ensure_plan(self, plan: Plan) -> None: ...

    async def replace_zone_alerts(
        self, zone_ids: Sequence[UUID], alerts: Sequence[ZoneAlert]
    ) -> None: ...

    async def add_zone_alert(self, alert: ZoneAlert) -> None: ...

    async def remove_zone_alert(self, alert_id: UUID) -> UUID | None: ...

    async def alert_severities(self, zone_id: UUID) -> list[str]: ...

    async def open_ticket_severities(self, zone_id: UUID) -> list[str]: ...

    async def zone_status(self, zone_id: UUID) -> str | None: ...

    async def set_zone_status(self, zone_id: UUID, status: str, at: datetime) -> None: ...

    async def open_auto_ticket(self, zone_id: UUID) -> TicketRow | None: ...

    async def ticket(self, incident_id: UUID, *, lock: bool = False) -> TicketRow | None: ...

    async def insert_ticket(
        self,
        *,
        incident_id: UUID,
        habitat_id: UUID,
        zone_id: UUID,
        type_key: str,
        source: str,
        source_alert_id: UUID | None,
        reported_by: UUID | None,
        title: str,
        description: str,
        severity: str,
        at: datetime,
    ) -> int:
        """Inserts the ticket and returns its sequential number."""
        ...

    async def set_severity(self, incident_id: UUID, severity: str) -> None: ...

    async def set_status(self, incident_id: UUID, status: str, at: datetime) -> None: ...

    async def mark_values_normal(self, incident_id: UUID, at: datetime) -> None: ...

    async def add_update(
        self, incident_id: UUID, kind: str, note: str | None, author_id: UUID | None, at: datetime
    ) -> None: ...
