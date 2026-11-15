"""Operación del outbox: reencolar un evento muerto y limpiar los ya entregados."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.platform.outbox.publisher import NOTIFY_CHANNEL

ReplayOutcome = Literal["replayed", "not_dead", "not_found"]
RETENTION = timedelta(hours=24)


async def replay_event(session: AsyncSession, outbox_id: int) -> ReplayOutcome:
    """Un evento `dead` vuelve a `pending` con los intentos en cero.

    Los consumidores que ya lo procesaron no lo repiten: su marca sigue en el inbox.
    """
    status = (
        await session.execute(
            text("SELECT status FROM platform.outbox_event WHERE id = :i FOR UPDATE"),
            {"i": outbox_id},
        )
    ).scalar_one_or_none()
    if status is None:
        return "not_found"
    if status != "dead":
        return "not_dead"
    await session.execute(
        text(
            "UPDATE platform.outbox_event SET status = 'pending', attempts = 0, last_error = NULL, "
            "next_attempt_at = now() WHERE id = :i"
        ),
        {"i": outbox_id},
    )
    await session.execute(text(f"NOTIFY {NOTIFY_CHANNEL}"))
    return "replayed"


async def purge_done(session: AsyncSession, older_than: timedelta = RETENTION) -> int:
    """Borra los eventos `done` más viejos que la retención. Devuelve cuántos borró."""
    result = await session.execute(
        text(
            "DELETE FROM platform.outbox_event WHERE status = 'done' "
            "AND occurred_at < now() - make_interval(secs => :s)"
        ),
        {"s": older_than.total_seconds()},
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
