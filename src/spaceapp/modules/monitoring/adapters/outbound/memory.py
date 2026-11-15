"""In-memory alert repository, for tests and development without a database."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from spaceapp.modules.monitoring.domain.engine import RuleHit
from spaceapp.modules.monitoring.domain.lifecycle import ActiveAlert, AlertRecord
from spaceapp.modules.monitoring.domain.rules import RuleCatalog


class InMemoryAlertRepository:
    def __init__(self) -> None:
        self._alerts: dict[UUID, dict[str, Any]] = {}

    async def ensure_rules(self, catalog: RuleCatalog) -> None:
        return None

    async def active_for_zone(self, habitat_id: UUID, zone_id: UUID) -> list[ActiveAlert]:
        return [
            ActiveAlert(
                a["id"], a["rule_key"], a["zone_id"], a["severity"], a["status"], a["streak"]
            )
            for a in self._alerts.values()
            if a["habitat_id"] == habitat_id
            and a["zone_id"] == zone_id
            and a["status"] != "resolved"
        ]

    async def add(self, habitat_id: UUID, zone_id: UUID, hit: RuleHit, raised_at: datetime) -> UUID:
        alert_id = uuid4()
        self._alerts[alert_id] = {
            "id": alert_id,
            "habitat_id": habitat_id,
            "zone_id": zone_id,
            "rule_key": hit.rule_key,
            "severity": hit.severity,
            "status": "raised",
            "streak": 0,
            "raised_at": raised_at,
            "evidence": hit.as_evidence(),
        }
        return alert_id

    async def touch(self, alert_id: UUID, evidence: dict[str, Any]) -> None:
        self._alerts[alert_id].update(evidence=evidence, streak=0)

    async def set_streak(self, alert_id: UUID, streak: int) -> None:
        self._alerts[alert_id]["streak"] = streak

    async def resolve(self, alert_id: UUID, resolved_at: datetime) -> int:
        a = self._alerts[alert_id]
        a.update(status="resolved", resolved_at=resolved_at)
        return int((resolved_at - a["raised_at"]).total_seconds())

    async def get(self, alert_id: UUID) -> AlertRecord | None:
        a = self._alerts.get(alert_id)
        return AlertRecord(a["id"], a["habitat_id"], a["zone_id"], a["status"]) if a else None

    async def acknowledge(
        self, alert_id: UUID, crew_member_id: UUID, note: str | None, at: datetime
    ) -> None:
        self._alerts[alert_id].update(status="acknowledged", acknowledged_at=at)
