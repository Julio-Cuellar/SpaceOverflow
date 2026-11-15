"""Endpoint `/ws`: a single push channel. User actions go through GraphQL."""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from spaceapp.modules.realtime.application.hub import Client, Hub
from spaceapp.modules.realtime.domain.messages import system_message
from spaceapp.modules.realtime.ports import OutboxReplay

RESUME_LIMIT = 1000
# With no messages for this long the server sends `ping` to keep the connection alive.
PING_INTERVAL_S = 15


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _error(client: Client, reason: str) -> None:
    client.queue.push(system_message("error", {"reason": reason}, _now()))


async def _handle(client: Client, raw: str, replay: OutboxReplay | None) -> None:
    try:
        msg: Any = json.loads(raw)
    except json.JSONDecodeError:
        return _error(client, "the message is not JSON")
    if not isinstance(msg, dict):
        return _error(client, "the message must be a JSON object")
    kind = msg.get("type")
    match kind:
        case "ping":
            client.queue.push(system_message("pong", {"ts": msg.get("ts")}, _now()))
        case "subscribe" | "unsubscribe":
            topics = msg.get("topics")
            if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
                return _error(client, "topics must be a list of strings")
            try:
                (client.subscribe if kind == "subscribe" else client.unsubscribe)(topics)
            except ValueError as exc:
                return _error(client, str(exc))
            client.queue.push(system_message("subscribed", {"topics": client.topics}, _now()))
        case "resume":
            after = msg.get("after_outbox_id")
            if not isinstance(after, int) or isinstance(after, bool) or after < 0:
                return _error(
                    client, "after_outbox_id must be an integer greater than or equal to 0"
                )
            if replay is None:
                return _error(client, "resume is not available without an outbox")
            missed = [m for m in await replay.after(after, RESUME_LIMIT) if client.accepts(m)]
            for m in missed:
                client.queue.push(m)
            last = missed[-1].seq if missed else after
            client.queue.push(
                system_message("resumed", {"count": len(missed), "last_seq": last}, _now())
            )
        case _:
            _error(client, f"unknown message type: {kind!r}")


def build_router(
    hub: Hub, replay: OutboxReplay | None, *, ping_interval: float = PING_INTERVAL_S
) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        client = hub.connect()

        async def sender() -> None:
            while True:
                try:
                    batch = await asyncio.wait_for(client.queue.get(), ping_interval)
                except TimeoutError:
                    batch = [system_message("ping", {}, _now())]
                for message in batch:
                    await ws.send_json(message.as_json())

        send_task = asyncio.create_task(sender())
        try:
            while True:
                await _handle(client, await ws.receive_text(), replay)
        except WebSocketDisconnect:
            pass
        finally:
            hub.disconnect(client)
            send_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await send_task

    return router
