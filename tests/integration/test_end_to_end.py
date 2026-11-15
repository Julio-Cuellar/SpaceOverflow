"""End to end (F5, task 5.5): scenario → alert over /ws in under 1 s → acknowledge over /graphql.

The app runs as in production (relay with LISTEN/NOTIFY and its own engine). The test pushes
simulated readings with a fake clock into the same database, at real pace: one more tick only when
the relay has finished the previous one (live, at most one tick per second arrives).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from spaceapp.main import create_app
from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.platform.config import Settings
from spaceapp.platform.outbox import outbox_stats
from tests.integration.telemetry.conftest import T0

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
LATENCY_GOAL_S = 1.0


async def _drained(session_factory: Any, limit_s: float = 10) -> float:
    """Seconds until the relay leaves the outbox with nothing pending."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    while loop.time() - start < limit_s:
        async with session_factory() as session:
            if (await outbox_stats(session)).pending == 0:
                return loop.time() - start
        await asyncio.sleep(0.02)
    raise TimeoutError("the relay did not empty the outbox")


async def _receive(ws: Any, limit_s: float = 30) -> dict[str, Any]:
    message: dict[str, Any] = await asyncio.wait_for(asyncio.to_thread(ws.receive_json), limit_s)
    return message


async def test_a_co2_scenario_reaches_a_websocket_client_and_is_acknowledged_by_graphql(
    async_url: str, session_factory: Any
) -> None:
    settings = Settings(database_url=async_url, relay_enabled=True, rule_window_scale=1 / 60)
    sim = SimulationService(
        session_factory,
        SqlTelemetryRepository,
        load_layout(ROOT / "data" / "telemetry" / "sim_layout.json"),
        seed=7,
    )
    with TestClient(create_app(settings)) as client, client.websocket_connect("/ws") as ws:
        ws.send_json(
            {"type": "unsubscribe", "topics": ["telemetry", "assistant", "habitat", "crew"]}
        )
        assert (await _receive(ws))["data"]["topics"] == ["alerts"]

        def wait_for_alert() -> tuple[dict[str, Any], datetime]:
            # Read in parallel with the simulation to take the real arrival time.
            while True:
                message = ws.receive_json()
                if (
                    message["type"] == "alert.raised"
                    and message["data"]["rule_key"] == "env-co2-1h"
                ):
                    return message, datetime.now(UTC)

        reader = asyncio.create_task(asyncio.to_thread(wait_for_alert))
        await sim.ensure_sensors()
        slowest_tick = 0.0
        for step in range(0, 331, 5):
            now = T0 + timedelta(seconds=step)
            if step == 150:
                await sim.start_scenario("co2_slow", "lab", now=now)
            await sim.tick(now)
            slowest_tick = max(slowest_tick, await _drained(session_factory))
            if reader.done():
                break
        assert slowest_tick < 1.0, f"the relay took {slowest_tick:.3f} s to process a tick"
        raised, arrived = await asyncio.wait_for(reader, 30)
        latency = (arrived - datetime.fromisoformat(raised["at"])).total_seconds()
        assert raised["seq"] is not None, "an alert carries the outbox id so it can be resumed"
        assert raised["data"]["severity"] == "ALERT"

        ack = client.post(
            "/graphql",
            json={
                "query": """mutation($id: ID!) { acknowledgeAlert(id: $id) {
                  __typename ... on AlertAcknowledgedPayload { alert { status } } } }""",
                "variables": {"id": raised["data"]["alert_id"]},
            },
        ).json()
        assert ack["data"]["acknowledgeAlert"] == {
            "__typename": "AlertAcknowledgedPayload",
            "alert": {"status": "ACKNOWLEDGED"},
        }
        while (message := await _receive(ws))["type"] != "alert.updated":
            pass
        assert message["data"]["alert_id"] == raised["data"]["alert_id"]
        assert message["data"]["status"] == "acknowledged"

        # A client that subscribes late recovers the ticket and the zone colour with `resume`.
        ws.send_json({"type": "subscribe", "topics": ["habitat"]})
        while (await _receive(ws))["type"] != "subscribed":
            pass
        ws.send_json({"type": "resume", "after_outbox_id": 0})
        replayed: list[dict[str, Any]] = []
        while (message := await _receive(ws))["type"] != "resumed":
            replayed.append(message)
        seqs = [m["seq"] for m in replayed]
        assert seqs == sorted(seqs) and len(seqs) == len(set(seqs)), (
            "in order and without duplicates"
        )
        habitat = {m["type"]: m["data"] for m in replayed if m["topic"] == "habitat"}
        assert habitat["incident.opened"]["severity"] == "ALERT"
        assert habitat["zone.status"]["status"] == "ALERT"
        assert habitat["zone.status"]["zone_id"] == raised["data"]["zone_id"]

    # From when Monitoring creates the event until it reaches the client (relay, outbox and gateway).
    print(f"alert latency {latency:.3f} s; slowest tick {slowest_tick:.3f} s")
    assert latency < LATENCY_GOAL_S, f"the alert took {latency:.3f} s to arrive"
