from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox.publisher import add_to_outbox


class UnitOfWork:
    """One transaction for the use case state and its events.

    If the block finishes successfully, state and events are committed together.
    If it fails, neither is.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active")
        return self._session

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self.session
        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def publish(self, event: EventEnvelope) -> None:
        await add_to_outbox(self.session, event)
