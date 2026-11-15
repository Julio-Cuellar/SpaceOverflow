from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class OutboxStats:
    pending: int
    dead: int
    oldest_pending_age_s: float | None


async def outbox_stats(session: AsyncSession) -> OutboxStats:
    row = (
        await session.execute(
            text(
                """
                SELECT count(*) FILTER (WHERE status = 'pending')  AS pending,
                       count(*) FILTER (WHERE status = 'dead')     AS dead,
                       extract(
                         epoch FROM now() - min(occurred_at) FILTER (WHERE status = 'pending')
                       )                                           AS lag
                FROM platform.outbox_event
                """
            )
        )
    ).one()
    return OutboxStats(
        int(row.pending), int(row.dead), float(row.lag) if row.lag is not None else None
    )
