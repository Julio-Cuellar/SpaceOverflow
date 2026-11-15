"""Lectura del outbox para numerar los mensajes y reenviarlos con `resume`."""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.realtime.domain.messages import REPLAYABLE_TYPES, WsMessage, translate
from spaceapp.platform.events import EventEnvelope

# Los eventos `done` se conservan 24 h (plan, sección 7).
_AFTER = text(
    """
    SELECT id, event_id, type, version, aggregate_type, aggregate_id, partition_key,
           correlation_id, causation_id, payload, occurred_at
    FROM platform.outbox_event
    WHERE id > :after AND status = 'done' AND type = ANY(CAST(:types AS text[]))
      AND occurred_at > now() - interval '24 hours'
    ORDER BY id
    LIMIT :n
    """
)


async def seq_of(session: AsyncSession | None, event_id: UUID) -> int | None:
    """Id del outbox del evento. Sin sesión (bus en memoria) no hay numeración."""
    if session is None:
        return None
    value = (
        await session.execute(
            text("SELECT id FROM platform.outbox_event WHERE event_id = :e"), {"e": event_id}
        )
    ).scalar_one_or_none()
    return int(value) if value is not None else None


class SqlOutboxReplay:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def after(self, after_id: int, limit: int) -> Sequence[WsMessage]:
        async with self._sf() as session:
            rows = (
                (
                    await session.execute(
                        _AFTER, {"after": after_id, "types": list(REPLAYABLE_TYPES), "n": limit}
                    )
                )
                .mappings()
                .all()
            )
        out: list[WsMessage] = []
        for row in rows:
            payload = row["payload"]
            envelope = EventEnvelope(
                event_id=row["event_id"],
                type=row["type"],
                version=row["version"],
                occurred_at=row["occurred_at"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                partition_key=row["partition_key"],
                correlation_id=row["correlation_id"],
                causation_id=row["causation_id"],
                payload=json.loads(payload) if isinstance(payload, str) else payload,
            )
            out.extend(m.with_seq(int(row["id"])) for m in translate(envelope))
        return out
