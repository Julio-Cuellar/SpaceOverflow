"""Operations routes (development profiles only). R8: requeue a dead outbox event."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.platform.outbox import replay_event


def build_router(session_factory: Callable[[], async_sessionmaker[AsyncSession]]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/admin", tags=["operations"])

    @router.post("/outbox/{event_id}:replay")
    async def replay(event_id: int) -> dict[str, object]:
        try:
            async with session_factory()() as session, session.begin():
                outcome = await replay_event(session, event_id)
        except OSError as exc:
            raise HTTPException(503, "the database is not responding") from exc
        if outcome == "not_found":
            raise HTTPException(404, f"event {event_id} does not exist in the outbox")
        if outcome == "not_dead":
            raise HTTPException(409, f"event {event_id} is not dead: it is not requeued")
        return {"id": event_id, "status": outcome}

    return router
