"""Crew repository on PostgreSQL. Works inside the received transaction."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.crew.domain.members import CrewMember


class SqlCrewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert(self, members: Sequence[CrewMember]) -> None:
        for m in members:
            await self._s.execute(
                text(
                    "INSERT INTO crew.member (id, habitat_id, code, name, role, portrait) "
                    "VALUES (:id, :h, :c, :n, :r, :p) ON CONFLICT (id) DO UPDATE SET "
                    "name = EXCLUDED.name, role = EXCLUDED.role, portrait = EXCLUDED.portrait"
                ),
                {
                    "id": m.id,
                    "h": m.habitat_id,
                    "c": m.code,
                    "n": m.name,
                    "r": m.role,
                    "p": m.portrait,
                },
            )
