"""Read-only queries of Facility (for the interface and other modules)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.facility.domain.incidents import incident_code


@dataclass(frozen=True)
class ZoneView:
    id: UUID
    code: str
    name: str
    kind: str
    deck: int
    layout: dict[str, Any]
    status: str
    open_incidents: int


@dataclass(frozen=True)
class IncidentView:
    id: UUID
    habitat_id: UUID
    zone_id: UUID
    type_key: str
    source: str
    source_alert_id: UUID | None
    title: str
    description: str
    severity: str
    status: str
    opened_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    values_normal_at: datetime | None
    number: int

    @property
    def code(self) -> str:
        return incident_code(self.number)


@dataclass(frozen=True)
class IncidentUpdateView:
    kind: str
    note: str | None
    author_id: UUID | None
    at: datetime


_INCIDENT = (
    "SELECT id, habitat_id, zone_id, type_key, source, source_alert_id, title, description, "
    "severity, status, opened_at, acknowledged_at, resolved_at, values_normal_at, number "
    "FROM facility.incident"
)


class ShipQuery:
    """Habitat zones with their color and their open tickets."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def zones(self, habitat_id: UUID) -> list[ZoneView]:
        sql = (
            "SELECT z.id, z.code, z.name, z.kind, z.deck, z.layout, z.status, "
            "(SELECT count(*) FROM facility.incident i WHERE i.zone_id = z.id "
            " AND i.status <> 'resolved') FROM facility.zone z WHERE z.habitat_id = :h "
            "ORDER BY z.deck, (z.layout->>'x')::numeric, z.code"
        )
        async with self._sf() as session:
            rows = (await session.execute(text(sql), {"h": habitat_id})).all()
        return [
            ZoneView(
                r[0],
                r[1],
                r[2],
                r[3],
                r[4],
                json.loads(r[5]) if isinstance(r[5], str) else r[5],
                r[6],
                int(r[7]),
            )
            for r in rows
        ]


class IncidentQuery:
    """Tickets from newest to oldest, with keyset pagination."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def page(
        self,
        first: int,
        *,
        after: tuple[datetime, UUID] | None = None,
        status: str | None = None,
        zone_id: UUID | None = None,
    ) -> tuple[list[IncidentView], bool]:
        where: list[str] = []
        params: dict[str, Any] = {"n": first + 1}
        if after is not None:
            where.append("(opened_at, id) < (:at, :id)")
            params["at"], params["id"] = after
        if status is not None:
            where.append("status = :st")
            params["st"] = status
        if zone_id is not None:
            where.append("zone_id = :z")
            params["z"] = zone_id
        sql = _INCIDENT + (f" WHERE {' AND '.join(where)}" if where else "")
        sql += " ORDER BY opened_at DESC, id DESC LIMIT :n"
        async with self._sf() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [IncidentView(*r) for r in rows[:first]], len(rows) > first

    async def get(self, incident_id: UUID) -> IncidentView | None:
        async with self._sf() as session:
            row = (
                await session.execute(text(_INCIDENT + " WHERE id = :i"), {"i": incident_id})
            ).first()
        return IncidentView(*row) if row else None

    async def updates(self, incident_id: UUID) -> list[IncidentUpdateView]:
        async with self._sf() as session:
            rows = await session.execute(
                text(
                    "SELECT kind, note, author_id, at FROM facility.incident_update "
                    "WHERE incident_id = :i ORDER BY at, id"
                ),
                {"i": incident_id},
            )
            return [IncidentUpdateView(*r) for r in rows]
