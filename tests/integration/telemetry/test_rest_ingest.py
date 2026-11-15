import httpx
import pytest

from spaceapp.main import create_app
from spaceapp.platform.config import Settings
from tests.integration.telemetry.conftest import CO2, HABITAT, T0

pytestmark = pytest.mark.integration


def client(sf) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    app = create_app(Settings(), session_factory=sf)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def body(n: int = 2, **over):  # type: ignore[no-untyped-def]
    return {
        "habitat_id": str(HABITAT),
        "readings": [
            {
                "sensor_id": str(CO2),
                "ts": (T0.replace(second=i)).isoformat(),
                "value": 0.7 + i / 100,
            }
            for i in range(n)
        ],
        **over,
    }


async def test_a_valid_batch_answers_202_with_the_counts(session_factory, sensors):
    async with client(session_factory) as c:
        r = await c.post("/api/v1/telemetry/readings", json=body(3))
    assert r.status_code == 202
    assert (r.json()["accepted"], r.json()["duplicates"]) == (3, 0) and r.json()["batch_id"]


async def test_posting_it_again_is_idempotent(session_factory, sensors):
    async with client(session_factory) as c:
        await c.post("/api/v1/telemetry/readings", json=body(3))
        r = await c.post("/api/v1/telemetry/readings", json=body(3))
    assert r.status_code == 202 and (r.json()["accepted"], r.json()["duplicates"]) == (0, 3)


async def test_a_batch_of_501_readings_is_rejected_with_422(session_factory, sensors):
    payload = {
        "habitat_id": str(HABITAT),
        "readings": [
            {
                "sensor_id": str(CO2),
                "ts": (T0.replace(minute=i // 60, second=i % 60)).isoformat(),
                "value": 1.0,
            }
            for i in range(501)
        ],
    }
    async with client(session_factory) as c:
        assert (await c.post("/api/v1/telemetry/readings", json=payload)).status_code == 422


async def test_empty_batches_unknown_sensors_and_naive_timestamps_are_422(session_factory, sensors):
    async with client(session_factory) as c:
        empty = await c.post("/api/v1/telemetry/readings", json=body(0))
        ghost = body(1)
        ghost["readings"][0]["sensor_id"] = "00000000-0000-4000-8000-00000000dead"
        unknown = await c.post("/api/v1/telemetry/readings", json=ghost)
        naive = body(1)
        naive["readings"][0]["ts"] = "2026-11-14T12:00:00"
        no_tz = await c.post("/api/v1/telemetry/readings", json=naive)
    assert (empty.status_code, unknown.status_code, no_tz.status_code) == (422, 422, 422)
    assert "00000000-0000-4000-8000-00000000dead" in str(unknown.json())
