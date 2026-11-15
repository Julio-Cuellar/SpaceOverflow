"""Read-only queries this module exposes to other modules."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class CrewMemberView:
    id: UUID
    code: str
    name: str
    role: str
    portrait: int


class CrewQuery:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def directory(self, habitat_id: UUID) -> list[CrewMemberView]:
        """Who is on board, in portrait order."""
        async with self._sf() as session:
            rows = await session.execute(
                text(
                    "SELECT id, code, name, role, portrait FROM crew.member "
                    "WHERE habitat_id = :h ORDER BY portrait, code"
                ),
                {"h": habitat_id},
            )
            return [CrewMemberView(*row) for row in rows]
