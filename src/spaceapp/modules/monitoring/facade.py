"""Consultas de solo lectura que Monitoreo expone a otros módulos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.monitoring.domain.rules import RuleCatalog


@dataclass(frozen=True)
class ActiveAlertView:
    alert_id: UUID
    rule_key: str
    zone_id: UUID | None
    severity: str
    status: str
    raised_at: datetime
    evidence_state: str
    action_key: str


@dataclass(frozen=True)
class RuleView:
    key: str
    parameter: str
    severity: str
    source_requirement: str
    source_document: str
    evidence_state: str
    action_key: str
    hrp_hazard: str


class ActiveAlertsQuery:
    """Alertas activas. La usan Nave e incidencias y el Asistente."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def list(
        self, *, zone_id: UUID | None = None, habitat_id: UUID | None = None
    ) -> list[ActiveAlertView]:
        where, params = ["a.status <> 'resolved'"], {}
        if zone_id is not None:
            where.append("a.zone_id = :z")
            params["z"] = zone_id
        if habitat_id is not None:
            where.append("a.habitat_id = :h")
            params["h"] = habitat_id
        sql = (
            "SELECT a.id, r.key, a.zone_id, a.severity, a.status, a.raised_at, r.evidence_state, "
            "r.action_key FROM monitoring.alert a JOIN monitoring.rule r ON r.id = a.rule_id "
            f"WHERE {' AND '.join(where)} ORDER BY a.raised_at, a.id"
        )
        async with self._sf() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [ActiveAlertView(*r) for r in rows]


class RuleQuery:
    """Regla y acción de una alerta. La usa Conocimiento."""

    def __init__(self, catalog: RuleCatalog) -> None:
        self._rules = catalog.by_key()

    def get(self, key: str) -> RuleView | None:
        r = self._rules.get(key)
        if r is None:
            return None
        return RuleView(
            r.key,
            r.parameter,
            r.severity,
            r.source_requirement,
            r.source_document,
            r.evidence_state,
            r.action_key,
            r.hrp_hazard,
        )
