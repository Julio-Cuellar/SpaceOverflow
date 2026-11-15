"""Crew on PostgreSQL: the roster is stored once and the directory endpoint serves it."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.testclient import TestClient

from spaceapp.main import create_app
from spaceapp.modules.crew.adapters.outbound.json_data import load_roster
from spaceapp.modules.crew.adapters.outbound.sql import SqlCrewRepository
from spaceapp.modules.crew.application.service import CrewService
from spaceapp.modules.crew.domain.members import CrewMember
from spaceapp.modules.crew.facade import CrewQuery
from spaceapp.platform.config import Settings

pytestmark = pytest.mark.integration


def service(session_factory: Any) -> CrewService:
    return CrewService(session_factory, SqlCrewRepository)


async def test_registering_the_roster_twice_does_not_duplicate_it(session_factory: Any) -> None:
    roster = load_roster(Settings().crew_roster_path)

    await service(session_factory).register(roster)
    await service(session_factory).register(roster)

    members = await CrewQuery(session_factory).directory(roster[0].habitat_id)
    assert [m.portrait for m in members] == [1, 2, 3, 4]
    assert {m.name for m in members} == {m.name for m in roster}


async def test_registering_again_updates_name_and_role(session_factory: Any) -> None:
    first = CrewMember.create(
        habitat="transit-ship", code="cdr", name="A. Garcia", role="Commander", portrait=1
    )
    renamed = CrewMember.create(
        habitat="transit-ship", code="cdr", name="A. Garcia", role="Flight commander", portrait=1
    )

    await service(session_factory).register([first])
    await service(session_factory).register([renamed])

    (stored,) = await CrewQuery(session_factory).directory(first.habitat_id)
    assert stored.role == "Flight commander"
    assert stored.id == first.id


async def test_the_directory_endpoint_lists_the_crew_without_inventing_health_data(
    async_url: str, session_factory: Any
) -> None:
    roster = load_roster(Settings().crew_roster_path)
    await service(session_factory).register(roster)

    with TestClient(create_app(Settings(database_url=async_url))) as client:
        response = client.get("/api/v1/crew")

    assert response.status_code == 200
    crew = response.json()["crew"]
    assert [m["portrait"] for m in crew] == [1, 2, 3, 4]
    for member in crew:
        assert set(member) == {"id", "name", "role", "portrait", "state", "vitals"}
        # No wearable exists: the state is unknown and there are no readings.
        assert member["state"] is None
        assert member["vitals"] == []
