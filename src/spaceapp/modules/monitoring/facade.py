"""Consultas de solo lectura que Monitoreo expone a otros módulos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
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


@dataclass(frozen=True)
class AlertView:
    alert_id: UUID
    rule_key: str
    habitat_id: UUID
    zone_id: UUID | None
    severity: str
    status: str
    cause_hint: str | None
    evidence: dict[str, Any]
    evidence_state: str
    raised_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


_ALERT_SELECT = (
    "SELECT a.id, r.key, a.habitat_id, a.zone_id, a.severity, a.status, a.cause_hint, "
    "a.evidence, r.evidence_state, a.raised_at, a.acknowledged_at, a.resolved_at "
    "FROM monitoring.alert a JOIN monitoring.rule r ON r.id = a.rule_id"
)


def _alert_view(row: Any) -> AlertView:
    evidence = json.loads(row[7]) if isinstance(row[7], str) else row[7]
    return AlertView(
        alert_id=row[0],
        rule_key=row[1],
        habitat_id=row[2],
        zone_id=row[3],
        severity=row[4],
        status=row[5],
        cause_hint=row[6],
        evidence=evidence,
        evidence_state=row[8],
        raised_at=row[9],
        acknowledged_at=row[10],
        resolved_at=row[11],
    )


class AlertReadQuery:
    """Alertas para la interfaz: de la más nueva a la más vieja, con paginación por llave."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def page(
        self,
        first: int,
        *,
        after: tuple[datetime, UUID] | None = None,
        status: str | None = None,
    ) -> tuple[list[AlertView], bool]:
        """Hasta `first` alertas después de la llave `(raised_at, id)` y si quedan más."""
        where: list[str] = []
        params: dict[str, Any] = {"n": first + 1}
        if after is not None:
            where.append("(a.raised_at, a.id) < (:at, :id)")
            params["at"], params["id"] = after
        if status is not None:
            where.append("a.status = :st")
            params["st"] = status
        sql = _ALERT_SELECT + (f" WHERE {' AND '.join(where)}" if where else "")
        sql += " ORDER BY a.raised_at DESC, a.id DESC LIMIT :n"
        async with self._sf() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [_alert_view(r) for r in rows[:first]], len(rows) > first

    async def get(self, alert_id: UUID) -> AlertView | None:
        async with self._sf() as session:
            row = (
                await session.execute(text(_ALERT_SELECT + " WHERE a.id = :i"), {"i": alert_id})
            ).first()
        return _alert_view(row) if row else None


class RuleQuery:
    """Regla y acción de una alerta. La usan Conocimiento y la interfaz."""

    def __init__(self, catalog: RuleCatalog) -> None:
        self._rules = catalog.by_key()

    def all(self) -> list[RuleView]:
        return [view for key in self._rules if (view := self.get(key)) is not None]

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
