"""R9: inbound Ground plans. R5: cut and restore of the simulated link."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from spaceapp.modules.groundlink.application.ground import GroundControl
from spaceapp.modules.groundlink.application.receiver import PlanReceiver


class InboundPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: UUID
    plan_version: int = Field(ge=1)
    items: list[dict[str, Any]]
    hash: str


class LinkChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["UP", "DOWN"]
    delay_s: float | None = Field(default=None, ge=0, le=60)


def build_router(services: Callable[[], tuple[PlanReceiver, GroundControl]]) -> APIRouter:
    """`services` is called on every request: services are built once the database is up."""
    router = APIRouter(prefix="/api/v1/groundlink", tags=["ground link"])

    @router.post("/inbound/plans", status_code=202)
    async def inbound_plan(plan: InboundPlan) -> JSONResponse:
        receiver, _ = services()
        got = await receiver.receive(plan.batch_id, plan.plan_version, plan.items, plan.hash)
        if got.status == "rejected":
            return JSONResponse(
                status_code=422, content={"status": "rejected", "reason": got.reason}
            )
        code = 202 if got.status == "received" else 200
        return JSONResponse(status_code=code, content={"status": got.status})

    @router.put("/link")
    async def set_link(change: LinkChange) -> dict[str, object]:
        _, ground = services()
        link = await ground.set_link(change.state == "UP", change.delay_s)
        return {"state": "UP" if link.online else "DOWN", "delay_s": link.delay_s}

    return router
