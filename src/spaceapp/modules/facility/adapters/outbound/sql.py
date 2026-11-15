"""Facility repository on PostgreSQL. Works inside the received transaction."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.facility.domain.plan import Plan
from spaceapp.modules.facility.ports import TicketRow, ZoneAlert

_TICKET = "SELECT id, zone_id, type_key, source, severity, status FROM facility.incident"


class SqlFacilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def ensure_plan(self, plan: Plan) -> None:
        """Syncs habitat and zones with the floor plan. Each zone's status is preserved."""
        await self._s.execute(
            text(
                "INSERT INTO facility.habitat (id, code, name, kind, p_total_nominal_kpa) "
                "VALUES (:id, :c, :n, :k, :p) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, "
                "kind = EXCLUDED.kind, p_total_nominal_kpa = EXCLUDED.p_total_nominal_kpa"
            ),
            {
                "id": plan.habitat_id,
                "c": plan.habitat_code,
                "n": plan.habitat_name,
                "k": plan.habitat_kind,
                "p": plan.p_total_nominal_kpa,
            },
        )
        for z in plan.zones:
            await self._s.execute(
                text(
                    "INSERT INTO facility.zone (id, habitat_id, code, name, kind, deck, layout) "
                    "VALUES (:id, :h, :c, :n, :k, :d, CAST(:l AS jsonb)) ON CONFLICT (id) DO UPDATE "
                    "SET name = EXCLUDED.name, kind = EXCLUDED.kind, deck = EXCLUDED.deck, "
                    "layout = EXCLUDED.layout"
                ),
                {
                    "id": z.id,
                    "h": plan.habitat_id,
                    "c": z.code,
                    "n": z.name,
                    "k": z.kind,
                    "d": z.deck,
                    "l": json.dumps(z.layout, sort_keys=True),
                },
            )

    async def replace_zone_alerts(
        self, zone_ids: Sequence[UUID], alerts: Sequence[ZoneAlert]
    ) -> None:
        await self._s.execute(
            text("DELETE FROM facility.zone_alert WHERE zone_id = ANY(CAST(:z AS uuid[]))"),
            {"z": list(zone_ids)},
        )
        for a in alerts:
            await self.add_zone_alert(a)

    async def add_zone_alert(self, alert: ZoneAlert) -> None:
        await self._s.execute(
            text(
                "INSERT INTO facility.zone_alert (alert_id, zone_id, rule_key, severity, raised_at) "
                "VALUES (:a, :z, :r, :s, :t) ON CONFLICT (alert_id) DO NOTHING"
            ),
            {
                "a": alert.alert_id,
                "z": alert.zone_id,
                "r": alert.rule_key,
                "s": alert.severity,
                "t": alert.raised_at,
            },
        )

    async def remove_zone_alert(self, alert_id: UUID) -> UUID | None:
        zone = (
            await self._s.execute(
                text("DELETE FROM facility.zone_alert WHERE alert_id = :a RETURNING zone_id"),
                {"a": alert_id},
            )
        ).scalar_one_or_none()
        return zone if isinstance(zone, UUID) else None

    async def alert_severities(self, zone_id: UUID) -> list[str]:
        rows = await self._s.execute(
            text("SELECT severity FROM facility.zone_alert WHERE zone_id = :z"), {"z": zone_id}
        )
        return [r[0] for r in rows]

    async def open_ticket_severities(self, zone_id: UUID) -> list[str]:
        rows = await self._s.execute(
            text(
                "SELECT severity FROM facility.incident WHERE zone_id = :z AND status <> 'resolved'"
            ),
            {"z": zone_id},
        )
        return [r[0] for r in rows]

    async def zone_status(self, zone_id: UUID) -> str | None:
        value = (
            await self._s.execute(
                text("SELECT status FROM facility.zone WHERE id = :z FOR UPDATE"), {"z": zone_id}
            )
        ).scalar_one_or_none()
        return str(value) if value is not None else None

    async def set_zone_status(self, zone_id: UUID, status: str, at: datetime) -> None:
        await self._s.execute(
            text("UPDATE facility.zone SET status = :s, status_changed_at = :t WHERE id = :z"),
            {"s": status, "t": at, "z": zone_id},
        )

    async def open_auto_ticket(self, zone_id: UUID) -> TicketRow | None:
        row = (
            await self._s.execute(
                text(
                    _TICKET + " WHERE zone_id = :z AND source = 'ALERT' AND status <> 'resolved' "
                    "FOR UPDATE"
                ),
                {"z": zone_id},
            )
        ).first()
        return TicketRow(*row) if row else None

    async def ticket(self, incident_id: UUID, *, lock: bool = False) -> TicketRow | None:
        sql = _TICKET + " WHERE id = :i" + (" FOR UPDATE" if lock else "")
        row = (await self._s.execute(text(sql), {"i": incident_id})).first()
        return TicketRow(*row) if row else None

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
        number = await self._s.execute(
            text(
                "INSERT INTO facility.incident (id, habitat_id, zone_id, type_key, source, "
                "source_alert_id, reported_by, title, description, severity, opened_at) VALUES "
                "(:id, :h, :z, :t, :src, :a, :r, :title, :d, :sev, :at) RETURNING number"
            ),
            {
                "id": incident_id,
                "h": habitat_id,
                "z": zone_id,
                "t": type_key,
                "src": source,
                "a": source_alert_id,
                "r": reported_by,
                "title": title,
                "d": description,
                "sev": severity,
                "at": at,
            },
        )
        return int(number.scalar_one())

    async def set_severity(self, incident_id: UUID, severity: str) -> None:
        await self._s.execute(
            text("UPDATE facility.incident SET severity = :s WHERE id = :i"),
            {"s": severity, "i": incident_id},
        )

    async def set_status(self, incident_id: UUID, status: str, at: datetime) -> None:
        column = {"acknowledged": "acknowledged_at", "resolved": "resolved_at"}[status]
        await self._s.execute(
            text(f"UPDATE facility.incident SET status = :s, {column} = :t WHERE id = :i"),
            {"s": status, "t": at, "i": incident_id},
        )

    async def mark_values_normal(self, incident_id: UUID, at: datetime) -> None:
        await self._s.execute(
            text("UPDATE facility.incident SET values_normal_at = :t WHERE id = :i"),
            {"t": at, "i": incident_id},
        )

    async def add_update(
        self, incident_id: UUID, kind: str, note: str | None, author_id: UUID | None, at: datetime
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO facility.incident_update (id, incident_id, kind, note, author_id, at) "
                "VALUES (:id, :i, :k, :n, :a, :t)"
            ),
            {"id": uuid4(), "i": incident_id, "k": kind, "n": note, "a": author_id, "t": at},
        )
