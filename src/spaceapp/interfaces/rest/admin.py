"""Rutas de operación (solo perfiles de desarrollo). R8: reencolar un evento muerto del outbox."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.platform.outbox import replay_event


def build_router(session_factory: Callable[[], async_sessionmaker[AsyncSession]]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/admin", tags=["operación"])

    @router.post("/outbox/{event_id}:replay")
    async def replay(event_id: int) -> dict[str, object]:
        try:
            async with session_factory()() as session, session.begin():
                outcome = await replay_event(session, event_id)
        except OSError as exc:
            raise HTTPException(503, "la base de datos no responde") from exc
        if outcome == "not_found":
            raise HTTPException(404, f"no existe el evento {event_id} en el outbox")
        if outcome == "not_dead":
            raise HTTPException(409, f"el evento {event_id} no está muerto: no se reencola")
        return {"id": event_id, "status": outcome}

    return router
