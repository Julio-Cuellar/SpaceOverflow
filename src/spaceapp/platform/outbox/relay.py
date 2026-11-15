"""Relay del outbox: entrega al menos una vez, con inbox, reintentos y eventos muertos."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.platform.bus import HandlerContext, Subscription, SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox.admin import RETENTION, purge_done
from spaceapp.platform.outbox.publisher import NOTIFY_CHANNEL, add_to_outbox

log = logging.getLogger(__name__)

_SELECT_PENDING = text(
    """
    SELECT id, event_id, type, version, aggregate_type, aggregate_id, partition_key,
           correlation_id, causation_id, payload, occurred_at, attempts
    FROM platform.outbox_event
    WHERE status = 'pending' AND next_attempt_at <= now()
    ORDER BY id
    LIMIT :n
    FOR UPDATE SKIP LOCKED
    """
)
_INBOX = text(
    "INSERT INTO platform.inbox_processed (consumer, event_id) VALUES (:c, :e) "
    "ON CONFLICT DO NOTHING RETURNING 1"
)
_DONE = text("UPDATE platform.outbox_event SET status = 'done', last_error = NULL WHERE id = :id")
_RETRY = text(
    "UPDATE platform.outbox_event SET status = :status, attempts = :attempts, "
    "last_error = :err, next_attempt_at = now() + make_interval(secs => :secs) WHERE id = :id"
)


def backoff_seconds(attempts: int) -> int:
    """1, 2, 4, 8 … con tope de 60 s."""
    return min(60, 1 << (attempts - 1))


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: SubscriptionRegistry,
        *,
        batch_size: int = 100,
        max_attempts: int = 8,
        poll_interval: float = 0.5,
        listen_dsn: str | None = None,
        purge_interval: float = 600,
    ) -> None:
        self._sf = session_factory
        self._registry = registry
        self.batch_size = batch_size
        self.max_attempts = max_attempts
        self.poll_interval = poll_interval
        self._listen_dsn = listen_dsn
        self.purge_interval = purge_interval

    async def run_once(self) -> int:
        """Procesa un lote de pendientes en orden de id. Devuelve cuántos tomó."""
        async with self._sf() as session, session.begin():
            rows = (await session.execute(_SELECT_PENDING, {"n": self.batch_size})).mappings().all()
            for row in rows:
                await self._process(session, row)
            return len(rows)

    async def _process(self, session: AsyncSession, row: RowMapping) -> None:
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
        errors: list[str] = []
        for sub in self._registry.subscribers_for(envelope.type):
            try:
                await self._run_handler(sub, envelope)
            except Exception as exc:
                log.warning("handler %s falló con %s: %r", sub.consumer, envelope.type, exc)
                errors.append(f"{sub.consumer}: {exc!r}")
        if not errors:
            await session.execute(_DONE, {"id": row["id"]})
            return
        attempts = int(row["attempts"]) + 1
        await session.execute(
            _RETRY,
            {
                "id": row["id"],
                "attempts": attempts,
                "err": "; ".join(errors),
                "status": "dead" if attempts >= self.max_attempts else "pending",
                "secs": backoff_seconds(attempts),
            },
        )

    async def _run_handler(self, sub: Subscription, envelope: EventEnvelope) -> None:
        """Cada handler corre en su propia transacción junto con su marca en el inbox."""
        async with self._sf() as hs, hs.begin():
            fresh = (await hs.execute(_INBOX, {"c": sub.consumer, "e": envelope.event_id})).first()
            if fresh is None:  # ya se procesó: se omite
                return

            async def publish(event: EventEnvelope) -> None:
                await add_to_outbox(hs, event)

            await sub.handler(envelope, HandlerContext(publish=publish, session=hs))

    async def run_forever(self, stop: asyncio.Event) -> None:
        """Se despierta con LISTEN/NOTIFY y, como red de seguridad, por sondeo."""
        wake = asyncio.Event()
        conn: asyncpg.Connection | None = None
        if self._listen_dsn:
            conn = await asyncpg.connect(self._listen_dsn)
            await conn.add_listener(NOTIFY_CHANNEL, lambda *_: wake.set())
        loop = asyncio.get_running_loop()
        next_purge = loop.time()
        try:
            while not stop.is_set():
                wake.clear()
                if loop.time() >= next_purge:
                    next_purge = loop.time() + self.purge_interval
                    await self._purge()
                try:
                    if await self.run_once():
                        continue
                except Exception:
                    log.exception("el relay no pudo leer el outbox")
                await self._sleep(wake, stop)
        finally:
            if conn is not None:
                await conn.close()

    async def _purge(self) -> None:
        """Los eventos entregados se conservan 24 h (para `resume`) y después se borran."""
        try:
            async with self._sf() as session, session.begin():
                purged = await purge_done(session, RETENTION)
            if purged:
                log.info("se borraron %d eventos entregados del outbox", purged)
        except Exception:
            log.exception("no se pudo limpiar el outbox")

    async def _sleep(self, wake: asyncio.Event, stop: asyncio.Event) -> None:
        tasks = {asyncio.create_task(wake.wait()), asyncio.create_task(stop.wait())}
        _, pending = await asyncio.wait(
            tasks, timeout=self.poll_interval, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t
