"""Distribution of messages to connected clients, with a bounded queue per client."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from spaceapp.modules.realtime.domain.messages import TOPICS, WsMessage

TICK = "telemetry.tick"


def _tick_key(m: WsMessage) -> tuple[object, object]:
    return (m.data.get("zone_id"), m.data.get("metric"))


class ClientQueue:
    """Up to `max_pending` messages. Ticks are dropped before anything else.

    A tick replaces the pending one for the same zone and metric (only the latest value matters).
    All other messages, alerts included, are never dropped.
    """

    def __init__(self, max_pending: int = 500) -> None:
        self._max = max_pending
        self._items: list[WsMessage] = []
        self._wake = asyncio.Event()
        self.dropped = 0

    def push(self, message: WsMessage) -> None:
        if message.type == TICK:
            key = _tick_key(message)
            self._items = [m for m in self._items if not (m.type == TICK and _tick_key(m) == key)]
            if len(self._items) >= self._max and not self._drop_oldest_tick():
                self.dropped += 1  # there are no ticks to remove: the incoming one is dropped
                return
        else:
            while len(self._items) >= self._max and self._drop_oldest_tick():
                pass
        self._items.append(message)
        self._wake.set()

    def _drop_oldest_tick(self) -> bool:
        for i, m in enumerate(self._items):
            if m.type == TICK:
                del self._items[i]
                self.dropped += 1
                return True
        return False

    def drain(self) -> list[WsMessage]:
        out, self._items = self._items, []
        self._wake.clear()
        return out

    async def get(self) -> list[WsMessage]:
        while not self._items:
            self._wake.clear()
            await self._wake.wait()
        return self.drain()


class Client:
    def __init__(self, max_pending: int = 500) -> None:
        self.queue = ClientQueue(max_pending)
        self._topics: set[str] = set(TOPICS)

    @property
    def topics(self) -> list[str]:
        return sorted(self._topics)

    def subscribe(self, topics: Iterable[str]) -> None:
        wanted = list(topics)
        _check(wanted)
        self._topics.update(wanted)

    def unsubscribe(self, topics: Iterable[str]) -> None:
        wanted = list(topics)
        _check(wanted)
        self._topics.difference_update(wanted)

    def accepts(self, message: WsMessage) -> bool:
        return message.topic in self._topics


def _check(topics: list[str]) -> None:
    for t in topics:
        if t not in TOPICS:
            raise ValueError(f"unknown topic: {t}")


class Hub:
    def __init__(self, max_pending: int = 500) -> None:
        self._max = max_pending
        self._clients: list[Client] = []

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def connect(self) -> Client:
        client = Client(self._max)
        self._clients.append(client)
        return client

    def disconnect(self, client: Client) -> None:
        if client in self._clients:
            self._clients.remove(client)

    async def broadcast(self, message: WsMessage) -> None:
        for client in list(self._clients):
            if client.accepts(message):
                client.queue.push(message)
