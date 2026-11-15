import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.platform.events import EventEnvelope

NOTIFY_CHANNEL = "outbox_new"

_INSERT = text(
    """
    INSERT INTO platform.outbox_event
      (event_id, type, version, aggregate_type, aggregate_id, partition_key,
       correlation_id, causation_id, payload, occurred_at)
    VALUES
      (:event_id, :type, :version, :aggregate_type, :aggregate_id, :partition_key,
       :correlation_id, :causation_id, CAST(:payload AS jsonb), :occurred_at)
    """
)


async def add_to_outbox(session: AsyncSession, event: EventEnvelope) -> None:
    """Inserts the event in the `session` transaction. The NOTIFY goes out on commit."""
    await session.execute(
        _INSERT,
        {
            "event_id": event.event_id,
            "type": event.type,
            "version": event.version,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "partition_key": event.partition_key,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "payload": json.dumps(event.payload),
            "occurred_at": event.occurred_at,
        },
    )
    await session.execute(
        text("SELECT pg_notify(:ch, :id)"), {"ch": NOTIFY_CHANNEL, "id": str(event.event_id)}
    )
