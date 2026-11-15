"""Event bus ports and their in-memory adapter.

Handlers are written once and run the same way on the in-memory bus (development and
tests) or on the real outbox: they receive the event and a `HandlerContext`.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NamedTuple, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.platform.events import EventEnvelope

PublishFn = Callable[[EventEnvelope], Awaitable[None]]


@dataclass(frozen=True)
class HandlerContext:
    """What a handler can use. `session` is None on the in-memory bus."""

    publish: PublishFn
    session: AsyncSession | None = None


Handler = Callable[[EventEnvelope, HandlerContext], Awaitable[None]]


class EventPublisher(Protocol):
    async def publish(self, event: EventEnvelope) -> None: ...


class EventBus(Protocol):
    def subscribe(self, event_type: str, consumer: str, handler: Handler) -> None: ...


class Subscription(NamedTuple):
    consumer: str
    handler: Handler


class SubscriptionRegistry:
    def __init__(self) -> None:
        self._subs: dict[str, list[Subscription]] = defaultdict(list)

    def subscribe(self, event_type: str, consumer: str, handler: Handler) -> None:
        if any(s.consumer == consumer for s in self._subs[event_type]):
            raise ValueError(f"{consumer!r} is already subscribed to {event_type!r}")
        self._subs[event_type].append(Subscription(consumer, handler))

    def subscribers_for(self, event_type: str) -> list[Subscription]:
        return list(self._subs.get(event_type, []))


class InMemoryEventBus(SubscriptionRegistry):
    """Immediate delivery, idempotent per (consumer, event) and in FIFO order.

    An event published from a handler is delivered when the handler finishes, just
    like with the outbox. A failing handler does not stop the others: the error is
    kept in `failures` and re-raised at the end.
    """

    def __init__(self) -> None:
        super().__init__()
        self._done: set[tuple[str, UUID]] = set()
        self._queue: deque[EventEnvelope] = deque()
        self._draining = False
        self.failures: list[tuple[str, BaseException]] = []

    async def publish(self, event: EventEnvelope) -> None:
        self._queue.append(event)
        if self._draining:
            return
        self._draining = True
        first_error: BaseException | None = None
        try:
            while self._queue:
                error = await self._dispatch(self._queue.popleft())
                first_error = first_error or error
        finally:
            self._draining = False
        if first_error is not None:
            raise first_error

    async def _dispatch(self, event: EventEnvelope) -> BaseException | None:
        ctx = HandlerContext(publish=self.publish)
        first: BaseException | None = None
        for sub in self.subscribers_for(event.type):
            key = (sub.consumer, event.event_id)
            if key in self._done:
                continue
            try:
                await sub.handler(event, ctx)
            except Exception as exc:
                self.failures.append((sub.consumer, exc))
                first = first or exc
            else:
                self._done.add(key)
        return first
