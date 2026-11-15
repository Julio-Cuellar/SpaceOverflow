"""Use case: put the crew of a habitat on record."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.crew.domain.members import CrewMember
from spaceapp.modules.crew.ports import CrewRepository


class CrewService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: Callable[[AsyncSession], CrewRepository],
    ) -> None:
        self._sf = session_factory
        self._repository = repository

    async def register(self, members: Sequence[CrewMember]) -> None:
        """Idempotent: a member that is already on record only has its name, role and portrait
        updated."""
        async with self._sf() as session, session.begin():
            await self._repository(session).upsert(members)
