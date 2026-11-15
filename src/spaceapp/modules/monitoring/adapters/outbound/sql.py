"""Repositorio de alertas sobre PostgreSQL. Trabaja en la transacción de la sesión recibida."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.monitoring.domain.engine import RuleHit
from spaceapp.modules.monitoring.domain.lifecycle import ActiveAlert, AlertRecord
from spaceapp.modules.monitoring.domain.rules import Rule, RuleCatalog

_RULE_COLUMNS = (
    "kind, parameter, operator, threshold, unit, window_s, severity, source_requirement, "
    "source_document, evidence_state, hrp_hazard, action_key, active, params, supersedes"
)


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _values(rule: Rule) -> dict[str, Any]:
    return {
        "kind": rule.kind,
        "parameter": rule.parameter,
        "operator": rule.operator,
        "threshold": rule.threshold,
        "unit": rule.unit,
        "window_s": rule.window_s,
        "severity": rule.severity,
        "source_requirement": rule.source_requirement,
        "source_document": rule.source_document,
        "evidence_state": rule.evidence_state,
        "hrp_hazard": rule.hrp_hazard,
        "action_key": rule.action_key,
        "active": rule.active,
        "params": json.dumps(dict(rule.params), sort_keys=True),
        "supersedes": json.dumps(list(rule.supersedes)),
    }


def _same(row: Any, rule: Rule) -> bool:
    return (
        row.kind == rule.kind
        and row.parameter == rule.parameter
        and row.operator == rule.operator
        and float(row.threshold) == rule.threshold
        and row.unit == rule.unit
        and row.window_s == rule.window_s
        and row.severity == rule.severity
        and row.source_requirement == rule.source_requirement
        and row.source_document == rule.source_document
        and row.evidence_state == rule.evidence_state
        and row.hrp_hazard == rule.hrp_hazard
        and row.action_key == rule.action_key
        and row.active == rule.active
        and _json(row.params) == dict(rule.params)
        and _json(row.supersedes) == list(rule.supersedes)
    )


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session
        self._rule_ids: dict[str, UUID] = {}

    async def ensure_rules(self, catalog: RuleCatalog) -> None:
        """Sincroniza el catálogo con la tabla. Una regla que cambia sube su versión."""
        existing = {
            r.key: r
            for r in (
                await self._s.execute(
                    text(f"SELECT id, key, version, {_RULE_COLUMNS} FROM monitoring.rule")
                )
            ).all()
        }
        for rule in catalog.rules:
            row = existing.get(rule.key)
            vals = _values(rule)
            if row is None:
                rule_id = uuid4()
                await self._s.execute(
                    text(
                        "INSERT INTO monitoring.rule (id, key, version, kind, parameter, operator, "
                        "threshold, unit, window_s, severity, source_requirement, source_document, "
                        "evidence_state, hrp_hazard, action_key, active, params, supersedes) VALUES "
                        "(:id, :key, 1, :kind, :parameter, :operator, :threshold, :unit, :window_s, "
                        ":severity, :source_requirement, :source_document, :evidence_state, "
                        ":hrp_hazard, :action_key, :active, CAST(:params AS jsonb), "
                        "CAST(:supersedes AS jsonb))"
                    ),
                    {"id": rule_id, "key": rule.key, **vals},
                )
            else:
                rule_id = row.id
                if not _same(row, rule):
                    await self._s.execute(
                        text(
                            "UPDATE monitoring.rule SET version = version + 1, kind=:kind, "
                            "parameter=:parameter, operator=:operator, threshold=:threshold, "
                            "unit=:unit, window_s=:window_s, severity=:severity, "
                            "source_requirement=:source_requirement, source_document=:source_document, "
                            "evidence_state=:evidence_state, hrp_hazard=:hrp_hazard, "
                            "action_key=:action_key, active=:active, params=CAST(:params AS jsonb), "
                            "supersedes=CAST(:supersedes AS jsonb) WHERE id=:id"
                        ),
                        {"id": rule_id, **vals},
                    )
            self._rule_ids[rule.key] = rule_id

    async def _rule_id(self, key: str) -> UUID:
        if key not in self._rule_ids:
            found = (
                await self._s.execute(
                    text("SELECT id FROM monitoring.rule WHERE key = :k"), {"k": key}
                )
            ).scalar_one_or_none()
            if found is None:
                raise LookupError(f"la regla {key!r} no está sincronizada: llame a ensure_rules")
            self._rule_ids[key] = found
        return self._rule_ids[key]

    async def active_for_zone(self, habitat_id: UUID, zone_id: UUID) -> list[ActiveAlert]:
        rows = await self._s.execute(
            text(
                "SELECT a.id, r.key, a.zone_id, a.severity, a.status, a.clear_streak "
                "FROM monitoring.alert a JOIN monitoring.rule r ON r.id = a.rule_id "
                "WHERE a.habitat_id = :h AND a.zone_id = :z AND a.status <> 'resolved' "
                "ORDER BY a.raised_at, a.id"
            ),
            {"h": habitat_id, "z": zone_id},
        )
        return [
            ActiveAlert(r.id, r.key, r.zone_id, r.severity, r.status, r.clear_streak) for r in rows
        ]

    async def add(self, habitat_id: UUID, zone_id: UUID, hit: RuleHit, raised_at: datetime) -> UUID:
        alert_id = uuid4()
        await self._s.execute(
            text(
                "INSERT INTO monitoring.alert (id, rule_id, habitat_id, zone_id, severity, status, "
                "cause_hint, evidence, dedupe_key, raised_at) VALUES (:id, :rule, :h, :z, :sev, "
                "'raised', 'AMBIENTE', CAST(:ev AS jsonb), :dk, :at)"
            ),
            {
                "id": alert_id,
                "rule": await self._rule_id(hit.rule_key),
                "h": habitat_id,
                "z": zone_id,
                "sev": hit.severity,
                "ev": json.dumps(hit.as_evidence()),
                "dk": f"{hit.rule_key}:{zone_id}",
                "at": raised_at,
            },
        )
        return alert_id

    async def touch(self, alert_id: UUID, evidence: dict[str, Any]) -> None:
        await self._s.execute(
            text(
                "UPDATE monitoring.alert SET evidence = CAST(:e AS jsonb), clear_streak = 0 WHERE id = :i"
            ),
            {"e": json.dumps(evidence), "i": alert_id},
        )

    async def set_streak(self, alert_id: UUID, streak: int) -> None:
        await self._s.execute(
            text("UPDATE monitoring.alert SET clear_streak = :n WHERE id = :i"),
            {"n": streak, "i": alert_id},
        )

    async def resolve(self, alert_id: UUID, resolved_at: datetime) -> int:
        raised_at = (
            await self._s.execute(
                text(
                    "UPDATE monitoring.alert SET status = 'resolved', resolved_at = :t, clear_streak = 0 "
                    "WHERE id = :i RETURNING raised_at"
                ),
                {"t": resolved_at, "i": alert_id},
            )
        ).scalar_one()
        return int((resolved_at - raised_at).total_seconds())

    async def get(self, alert_id: UUID) -> AlertRecord | None:
        row = (
            await self._s.execute(
                text("SELECT id, habitat_id, zone_id, status FROM monitoring.alert WHERE id = :i"),
                {"i": alert_id},
            )
        ).first()
        return AlertRecord(row.id, row.habitat_id, row.zone_id, row.status) if row else None

    async def acknowledge(
        self, alert_id: UUID, crew_member_id: UUID, note: str | None, at: datetime
    ) -> None:
        await self._s.execute(
            text(
                "UPDATE monitoring.alert SET status = 'acknowledged', acknowledged_at = :t WHERE id = :i"
            ),
            {"t": at, "i": alert_id},
        )
        await self._s.execute(
            text(
                "INSERT INTO monitoring.alert_ack (id, alert_id, crew_member_id, note, at) "
                "VALUES (:id, :a, :c, :n, :t)"
            ),
            {"id": uuid4(), "a": alert_id, "c": crew_member_id, "n": note, "t": at},
        )
