import httpx
import pytest
from sqlalchemy import text

from spaceapp.main import create_app
from spaceapp.platform.config import Settings

pytestmark = pytest.mark.integration


def client(sf) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    app = create_app(Settings(), session_factory=sf)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_a_scenario_can_be_started_and_stopped_over_rest(session_factory):
    async with client(session_factory) as c:
        start = await c.post(
            "/api/v1/sim/scenarios/co2_slow:start", json={"zone": "lab", "speed": 1.5}
        )
        stop = await c.post("/api/v1/sim/scenarios/co2_slow:stop", json={"zone": "lab"})
    assert start.status_code == 200 and start.json() == {
        "key": "co2_slow",
        "zone": "lab",
        "state": "started",
        "speed": 1.5,
    }
    assert stop.status_code == 200 and stop.json()["state"] == "stopped"
    async with session_factory() as s:
        kinds = (
            (
                await s.execute(
                    text(
                        "SELECT payload->>'state' FROM platform.outbox_event "
                        "WHERE type='telemetry.scenario_changed' ORDER BY id"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert kinds == ["started", "stopped"]


async def test_bad_requests_get_clear_status_codes(session_factory):
    async with client(session_factory) as c:
        unknown_action = await c.post("/api/v1/sim/scenarios/co2_slow:pausa", json={"zone": "lab"})
        unknown_scenario = await c.post(
            "/api/v1/sim/scenarios/terremoto:start", json={"zone": "lab"}
        )
        unknown_zone = await c.post("/api/v1/sim/scenarios/co2_slow:start", json={"zone": "narnia"})
        no_zone = await c.post("/api/v1/sim/scenarios/co2_slow:start", json={})
    assert unknown_action.status_code == 404 and unknown_scenario.status_code == 404
    assert unknown_zone.status_code == 422 and no_zone.status_code == 422
