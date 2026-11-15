"""Endpoint /ws: subscribe, unsubscribe, ping, resume y mensajes del servidor."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from spaceapp.modules.realtime.adapters.inbound.ws import build_router
from spaceapp.modules.realtime.application.hub import Hub
from spaceapp.modules.realtime.domain.messages import WsMessage


class FakeReplay:
    def __init__(self, messages: list[WsMessage]) -> None:
        self.messages = messages
        self.asked: list[int] = []

    async def after(self, after_id: int, limit: int) -> Sequence[WsMessage]:
        self.asked.append(after_id)
        return [m for m in self.messages if m.seq is not None and m.seq > after_id][:limit]


def alert(seq: int) -> WsMessage:
    return WsMessage(seq, "alerts", "alert.raised", "2026-11-14T20:00:00+00:00", {"n": seq})


def tick(value: float = 1.0) -> WsMessage:
    return WsMessage(
        None, "telemetry", "telemetry.tick", "t", {"zone_id": "z", "metric": "co2", "value": value}
    )


@pytest.fixture
def setup() -> tuple[TestClient, Hub, FakeReplay]:
    hub = Hub()
    replay = FakeReplay([alert(1), alert(2), alert(3)])
    app = FastAPI()
    app.include_router(build_router(hub, replay))
    with TestClient(app) as client:
        yield client, hub, replay  # type: ignore[misc]


def push(client: TestClient, hub: Hub, msg: WsMessage) -> None:
    client.portal.call(hub.broadcast, msg)  # type: ignore[union-attr]


def test_a_connected_client_receives_the_messages_the_hub_broadcasts(setup: Any) -> None:
    client, hub, _ = setup
    with client.websocket_connect("/ws") as ws:
        push(client, hub, alert(7))
        got = ws.receive_json()
        assert got == {
            "seq": 7,
            "topic": "alerts",
            "type": "alert.raised",
            "at": "2026-11-14T20:00:00+00:00",
            "data": {"n": 7},
        }
    assert hub.client_count == 0


def test_unsubscribe_and_subscribe_change_what_arrives(setup: Any) -> None:
    client, hub, _ = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "unsubscribe", "topics": ["telemetry"]})
        reply = ws.receive_json()
        assert reply["type"] == "subscribed"
        assert reply["data"]["topics"] == ["alerts", "assistant", "crew", "habitat"]
        push(client, hub, tick())
        push(client, hub, alert(1))
        assert ws.receive_json()["type"] == "alert.raised"  # el tick no llegó
        ws.send_json({"type": "subscribe", "topics": ["telemetry"]})
        assert ws.receive_json()["data"]["topics"] == [
            "alerts",
            "assistant",
            "crew",
            "habitat",
            "telemetry",
        ]


def test_ping_is_answered_with_pong_and_the_same_ts(setup: Any) -> None:
    client, _, _ = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping", "ts": 123})
        got = ws.receive_json()
        assert (got["type"], got["data"]["ts"]) == ("pong", 123)


def test_resume_replays_what_the_client_missed_in_order(setup: Any) -> None:
    client, _, replay = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "resume", "after_outbox_id": 1})
        assert [ws.receive_json()["seq"] for _ in range(2)] == [2, 3]
        done = ws.receive_json()
        assert (done["type"], done["data"]["count"]) == ("resumed", 2)
    assert replay.asked == [1]


def test_resume_respects_the_topics_the_client_chose(setup: Any) -> None:
    client, _, _ = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "unsubscribe", "topics": ["alerts"]})
        ws.receive_json()
        ws.send_json({"type": "resume", "after_outbox_id": 0})
        done = ws.receive_json()
        assert (done["type"], done["data"]["count"]) == ("resumed", 0)


@pytest.mark.parametrize(
    "bad",
    [{"type": "nope"}, {"type": "subscribe", "topics": ["x"]}, {"type": "resume"}, [1, 2]],
)
def test_bad_client_messages_get_an_error_and_keep_the_connection(setup: Any, bad: Any) -> None:
    client, hub, _ = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_json(bad)
        assert ws.receive_json()["type"] == "error"
        push(client, hub, alert(1))
        assert ws.receive_json()["type"] == "alert.raised"


def test_invalid_json_gets_an_error(setup: Any) -> None:
    client, _, _ = setup
    with client.websocket_connect("/ws") as ws:
        ws.send_text("{no es json")
        assert ws.receive_json()["type"] == "error"


def test_resume_without_a_replay_source_is_an_error() -> None:
    app = FastAPI()
    app.include_router(build_router(Hub(), None))
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "resume", "after_outbox_id": 0})
        assert ws.receive_json()["type"] == "error"


def test_an_idle_connection_gets_a_server_ping() -> None:
    app = FastAPI()
    app.include_router(build_router(Hub(), None, ping_interval=0.05))
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        got = ws.receive_json()
        assert (got["topic"], got["type"], got["seq"]) == ("system", "ping", None)


def test_the_default_server_ping_is_every_15_seconds() -> None:
    from spaceapp.modules.realtime.adapters.inbound.ws import PING_INTERVAL_S

    assert PING_INTERVAL_S == 15
