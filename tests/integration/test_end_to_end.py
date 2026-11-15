"""Extremo a extremo (F5, tarea 5.5): escenario → alerta por /ws en menos de 1 s → reconocer por /graphql.

La app corre como en producción (relay con LISTEN/NOTIFY y su propio engine). La prueba empuja
lecturas simuladas con reloj falso en la misma base, a ritmo real: un tick más solo cuando el relay
terminó el anterior (en vivo llega como mucho un tick por segundo).
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
    """Segundos hasta que el relay deja el outbox sin pendientes."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    while loop.time() - start < limit_s:
        async with session_factory() as session:
            if (await outbox_stats(session)).pending == 0:
                return loop.time() - start
        await asyncio.sleep(0.02)
    raise TimeoutError("el relay no vació el outbox")


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
            # Se lee en paralelo con la simulación para tomar la hora real de llegada.
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
        assert slowest_tick < 1.0, f"el relay tardó {slowest_tick:.3f} s en procesar un tick"
        raised, arrived = await asyncio.wait_for(reader, 30)
        latency = (arrived - datetime.fromisoformat(raised["at"])).total_seconds()
        assert raised["seq"] is not None, "una alerta lleva el id del outbox para poder reanudar"
        assert raised["data"]["severity"] == "ALERTA"

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

        # Un cliente que se suscribe tarde recupera el ticket y el color de la zona con `resume`.
        ws.send_json({"type": "subscribe", "topics": ["habitat"]})
        while (await _receive(ws))["type"] != "subscribed":
            pass
        ws.send_json({"type": "resume", "after_outbox_id": 0})
        replayed: list[dict[str, Any]] = []
        while (message := await _receive(ws))["type"] != "resumed":
            replayed.append(message)
        seqs = [m["seq"] for m in replayed]
        assert seqs == sorted(seqs) and len(seqs) == len(set(seqs)), "en orden y sin duplicados"
        habitat = {m["type"]: m["data"] for m in replayed if m["topic"] == "habitat"}
        assert habitat["incident.opened"]["severity"] == "ALERTA"
        assert habitat["zone.status"]["status"] == "ALERTA"
        assert habitat["zone.status"]["zone_id"] == raised["data"]["zone_id"]

    # Desde que Monitoreo crea el evento hasta que llega al cliente (relay, outbox y gateway).
    print(f"latencia de la alerta {latency:.3f} s; tick más lento {slowest_tick:.3f} s")
    assert latency < LATENCY_GOAL_S, f"la alerta tardó {latency:.3f} s en llegar"
