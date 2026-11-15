"""Tareas y plan de Tierra por GraphQL sobre la app real (relay y enlace simulado con demora)."""

from __future__ import annotations

import time
from typing import Any

import pytest
from starlette.testclient import TestClient

from spaceapp.main import create_app
from spaceapp.platform.config import Settings

pytestmark = pytest.mark.integration

TASK = "id kind origin title status blockedReason effective templateId"
TASK_RESULT = f"""__typename ... on TaskPayload {{ alreadyDone task {{ {TASK} }} }}
  ... on TaskError {{ code message }}"""
GROUND = """appliedVersion templates { id title status cancelled }
  draft { version templates { title status cancelled } }
  published { version stage reason } link { online delaySeconds }"""
GROUND_RESULT = f"__typename ... on GroundControlView {{ {GROUND} }} ... on GroundError {{ code }}"


def gql(client: TestClient, query: str, **variables: Any) -> dict[str, Any]:
    got = client.post("/graphql", json={"query": query, "variables": variables}).json()
    assert "errors" not in got, got["errors"]
    data: dict[str, Any] = got["data"]
    return data


def test_the_crew_works_its_daily_tasks(session_factory: Any, async_url: str) -> None:
    with TestClient(create_app(Settings(database_url=async_url, relay_enabled=True))) as client:
        tasks = gql(client, f"{{ tasks {{ {TASK} }} streak }}")
        assert len(tasks["tasks"]) == 7 and tasks["streak"] == 0
        routine = next(t for t in tasks["tasks"] if t["kind"] == "SALUD")
        ship = next(t for t in tasks["tasks"] if t["kind"] == "NAVE")

        done = gql(
            client,
            f"mutation($id: ID!) {{ completeTask(id: $id, effective: true) {{ {TASK_RESULT} }} }}",
            id=routine["id"],
        )["completeTask"]
        assert done["task"]["status"] == "COMPLETADA" and done["task"]["effective"] is True
        assert gql(client, "{ streak }")["streak"] == 1

        blocked = gql(
            client,
            f'mutation($id: ID!) {{ blockTask(id: $id, reason: "Sin repuesto") {{ {TASK_RESULT} }} }}',
            id=ship["id"],
        )["blockTask"]
        assert blocked["task"]["blockedReason"] == "Sin repuesto"

        refused = gql(
            client,
            "mutation($id: ID!) { deleteTask(id: $id) { __typename ... on TaskError { code } } }",
            id=ship["id"],
        )["deleteTask"]
        assert refused == {"__typename": "TaskError", "code": "NOT_DELETABLE"}

        own = gql(
            client,
            f'mutation {{ createTask(kind: NAVE, title: "Ordenar el almacén") {{ {TASK_RESULT} }} }}',
        )["createTask"]["task"]
        assert own["origin"] == "TRIPULACION"
        deleted = gql(
            client,
            "mutation($id: ID!) { deleteTask(id: $id) { __typename ... on TaskDeleted { id } } }",
            id=own["id"],
        )["deleteTask"]
        assert deleted == {"__typename": "TaskDeleted", "id": own["id"]}


def test_ground_publishes_a_plan_that_reaches_the_crew(
    session_factory: Any, async_url: str
) -> None:
    with TestClient(create_app(Settings(database_url=async_url, relay_enabled=True))) as client:
        gql(
            client,
            "mutation { setGroundLink(online: true, delaySeconds: 0.1) { link { online } } }",
        )
        saved = gql(
            client,
            f'mutation {{ saveGroundTemplate(title: "Ejercicio de Tierra", kind: SALUD) {{ {GROUND_RESULT} }} }}',
        )["saveGroundTemplate"]
        assert saved["draft"]["templates"] == [
            {"title": "Ejercicio de Tierra", "status": "PENDIENTE", "cancelled": False}
        ]
        published = gql(client, f"mutation {{ publishGroundPlan {{ {GROUND_RESULT} }} }}")
        assert published["publishGroundPlan"]["published"]["stage"] == "EN_EL_ENLACE"

        stage, deadline = None, time.monotonic() + 15
        while stage != "CONFIRMADO" and time.monotonic() < deadline:
            time.sleep(0.1)
            view = gql(client, f"{{ groundControl {{ {GROUND} }} }}")["groundControl"]
            stage = view["published"]["stage"]
        assert stage == "CONFIRMADO", view
        assert view["appliedVersion"] == 1
        assert [(t["title"], t["status"]) for t in view["templates"]] == [
            ("Ejercicio de Tierra", "APLICADA")
        ]
        crew = gql(
            client, f"{{ tasks {{ {TASK} }} groundPlan {{ version rejected {{ reason }} }} }}"
        )
        assert any(t["origin"] == "TIERRA" for t in crew["tasks"])
        assert crew["groundPlan"] == {"version": 1, "rejected": []}

        busy = gql(client, f"mutation {{ publishGroundPlan {{ {GROUND_RESULT} }} }}")
        assert busy["publishGroundPlan"] == {
            "__typename": "GroundError",
            "code": "NOTHING_TO_PUBLISH",
        }
