"""R10: the crew directory the console reads (`VITE_CREW_DIRECTORY_URL`)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from spaceapp.modules.crew.facade import CrewQuery
from spaceapp.platform.ids import DEFAULT_HABITAT_CODE, habitat_id


def build_router(query: Callable[[], CrewQuery]) -> APIRouter:
    """`query` is called on every request: the session factory exists once the database is up."""
    router = APIRouter(prefix="/api/v1/crew", tags=["crew"])

    @router.get("")
    async def directory(habitat: str = DEFAULT_HABITAT_CODE) -> dict[str, Any]:
        """Who is on board. Health data is not served because none exists: the state is unknown
        (`null`) and `vitals` is empty until a real source of readings is connected."""
        return {
            "crew": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "role": m.role,
                    "portrait": m.portrait,
                    "state": None,
                    "vitals": [],
                }
                for m in await query().directory(habitat_id(habitat))
            ]
        }

    return router
