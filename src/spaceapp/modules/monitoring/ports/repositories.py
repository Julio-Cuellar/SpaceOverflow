"""Monitoring outbound ports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from spaceapp.modules.monitoring.domain.engine import RuleHit
from spaceapp.modules.monitoring.domain.lifecycle import ActiveAlert, AlertRecord
from spaceapp.modules.monitoring.domain.rules import RuleCatalog
from spaceapp.modules.monitoring.domain.series import Sample


class ReadingQuery(Protocol):
    """Readings per zone. Telemetry delivers them through its facade."""

    async def series(
        self, zone_id: UUID, metrics: Sequence[str], since: datetime, until: datetime
    ) -> dict[str, list[Sample]]: ...


class AlertRepository(Protocol):
    async def ensure_rules(self, catalog: RuleCatalog) -> None: ...

    async def active_for_zone(self, habitat_id: UUID, zone_id: UUID) -> list[ActiveAlert]: ...

    async def add(
        self, habitat_id: UUID, zone_id: UUID, hit: RuleHit, raised_at: datetime
    ) -> UUID: ...

    async def touch(self, alert_id: UUID, evidence: dict[str, Any]) -> None: ...

    async def set_streak(self, alert_id: UUID, streak: int) -> None: ...

    async def resolve(self, alert_id: UUID, resolved_at: datetime) -> int: ...

    async def get(self, alert_id: UUID) -> AlertRecord | None: ...

    async def acknowledge(
        self, alert_id: UUID, crew_member_id: UUID, note: str | None, at: datetime
    ) -> None: ...
