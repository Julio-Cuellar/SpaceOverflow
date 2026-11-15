"""Event input of the gateway: translates what happens in the system and distributes it."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.realtime.application.hub import Hub
from spaceapp.modules.realtime.domain.messages import (
    REPLAYABLE_TYPES,
    TRANSLATED_TYPES,
    translate,
)
from spaceapp.platform.bus import EventBus, HandlerContext
from spaceapp.platform.events import EventEnvelope

CONSUMER = "realtime.fanout"

SeqOf = Callable[[AsyncSession | None, UUID], Awaitable[int | None]]


class RealtimeEvents:
    def __init__(self, hub: Hub, seq_of: SeqOf | None = None) -> None:
        self._hub = hub
        self._seq_of = seq_of

    async def on_event(self, envelope: EventEnvelope, ctx: HandlerContext) -> None:
        # The seq is the outbox id. Ticks do not carry it: they are not resent with `resume`.
        seq = None
        if self._seq_of is not None and envelope.type in REPLAYABLE_TYPES:
            seq = await self._seq_of(ctx.session, envelope.event_id)
        for message in translate(envelope):
            await self._hub.broadcast(message.with_seq(seq) if seq is not None else message)


def register_realtime(bus: EventBus, handler: RealtimeEvents) -> None:
    for event_type in TRANSLATED_TYPES:
        bus.subscribe(event_type, CONSUMER, handler.on_event)
