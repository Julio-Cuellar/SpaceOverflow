"""R1: batch ingestion of readings. R4: simulator scenario control."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, Field

from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.ingest_readings import UnknownSensors, ingest_readings
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.modules.telemetry.domain.readings import MAX_BATCH, InvalidBatch, ReadingIn
from spaceapp.modules.telemetry.domain.simulator import UnknownScenario, UnknownZone


class ReadingBody(BaseModel):
    sensor_id: UUID
    ts: AwareDatetime
    value: float
    quality: str = "ok"


class BatchBody(BaseModel):
    habitat_id: UUID
    batch_id: UUID | None = None
    readings: list[ReadingBody] = Field(min_length=1, max_length=MAX_BATCH)


class ScenarioBody(BaseModel):
    zone: str | None = None
    speed: float = Field(default=1.0, gt=0, le=20)


def build_router(get_simulation: Any) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/telemetry/readings", status_code=202)
    async def ingest(body: BatchBody, request: Request) -> dict[str, Any]:
        readings = [ReadingIn(r.sensor_id, r.ts, r.value, r.quality) for r in body.readings]
        try:
            result = await ingest_readings(
                request.app.state.session_factory,
                SqlTelemetryRepository,
                body.habitat_id,
                readings,
                batch_id=body.batch_id,
            )
        except UnknownSensors as err:
            raise HTTPException(
                422, detail={"unknown_sensor_ids": [str(i) for i in err.sensor_ids]}
            ) from err
        except InvalidBatch as err:
            raise HTTPException(422, detail=str(err)) from err
        return {
            "batch_id": str(result.batch_id),
            "accepted": result.accepted,
            "duplicates": result.duplicates,
        }

    @router.post("/api/v1/sim/scenarios/{key_action}")
    async def scenario(key_action: str, body: ScenarioBody, request: Request) -> dict[str, Any]:
        key, _, action = key_action.partition(":")
        if action not in ("start", "stop"):
            raise HTTPException(404, detail="the action must be start or stop")
        svc: SimulationService = get_simulation(request.app)
        try:
            if action == "start":
                await svc.start_scenario(key, body.zone, speed=body.speed)
                return {"key": key, "zone": body.zone, "state": "started", "speed": body.speed}
            await svc.stop_scenario(key, body.zone)
            return {"key": key, "zone": body.zone, "state": "stopped"}
        except UnknownScenario as err:
            raise HTTPException(404, detail=f"unknown scenario: {key}") from err
        except UnknownZone as err:
            raise HTTPException(422, detail=f"unknown zone: {body.zone}") from err
        except ValueError as err:
            raise HTTPException(422, detail=str(err)) from err

    return router
