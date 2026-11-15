"""Herramientas del agente de n8n: búsqueda de pasajes y alertas activas, solo lectura."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spaceapp.modules.assistant.adapters.inbound.rest import build_router
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog, passage_id
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"


class FakeAlerts:
    def titles(self) -> list[str]:
        return ["CO₂ alto en el laboratorio"]


@pytest.fixture
def rig() -> tuple[TestClient, RetrievalLog, uuid.UUID]:
    log = RetrievalLog()
    app = FastAPI()
    app.include_router(
        build_router(
            log=log,
            passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
            alerts=FakeAlerts(),
        )
    )
    turn = uuid.uuid4()
    log.open(turn)
    return TestClient(app), log, turn


def search(client: TestClient, turn: uuid.UUID | str, body: dict) -> object:  # type: ignore[type-arg]
    return client.post(f"/api/v1/assistant/tools/{turn}/search_passages", json=body)


def test_the_search_returns_the_passages_with_their_source(rig) -> None:  # type: ignore[no-untyped-def]
    client, _, turn = rig

    response = search(client, turn, {"query": "dolor de cabeza"})

    assert response.status_code == 200  # type: ignore[attr-defined]
    [first, *_] = response.json()["passages"]  # type: ignore[attr-defined]
    assert set(first) == {"passage_id", "text", "source"}
    assert "OCHMO-TB-004" in first["source"]
    assert "2.8" in first["text"]


def test_what_the_agent_sees_is_recorded_for_the_citations(rig) -> None:  # type: ignore[no-untyped-def]
    client, log, turn = rig

    response = search(client, turn, {"query": "dolor de cabeza"})

    ids = [p["passage_id"] for p in response.json()["passages"]]  # type: ignore[attr-defined]
    assert ids == [passage_id(c) for c in log.retrieved(turn)]
    assert ids


def test_a_question_without_a_passage_says_so_and_records_nothing(rig) -> None:  # type: ignore[no-untyped-def]
    client, log, turn = rig

    response = search(client, turn, {"query": "capital de Francia"})

    assert response.status_code == 200  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert body["passages"] == []
    assert "No hay pasajes" in body["message"]
    assert log.retrieved(turn) == []


def test_the_number_of_passages_is_capped(rig) -> None:  # type: ignore[no-untyped-def]
    client, _, turn = rig

    response = search(client, turn, {"query": "presión CO₂ cabeza", "k": 50})

    assert response.status_code == 422  # type: ignore[attr-defined]


@pytest.mark.parametrize("body", [{}, {"query": ""}, {"query": "   "}, {"query": 3}])
def test_a_missing_or_empty_query_is_rejected(rig, body) -> None:  # type: ignore[no-untyped-def]
    client, _, turn = rig

    assert search(client, turn, body).status_code == 422  # type: ignore[attr-defined]


def test_a_turn_that_is_not_open_gets_nothing(rig) -> None:  # type: ignore[no-untyped-def]
    client, log, turn = rig
    log.close(turn)

    response = search(client, turn, {"query": "dolor de cabeza"})

    assert response.status_code == 404  # type: ignore[attr-defined]


def test_an_unknown_turn_gets_nothing(rig) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = rig

    assert search(client, uuid.uuid4(), {"query": "dolor de cabeza"}).status_code == 404  # type: ignore[attr-defined]


def test_a_turn_id_that_is_not_a_uuid_is_rejected(rig) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = rig

    assert search(client, "no-es-un-uuid", {"query": "dolor"}).status_code == 422  # type: ignore[attr-defined]


def test_the_active_alerts_are_readable_during_the_turn(rig) -> None:  # type: ignore[no-untyped-def]
    client, _, turn = rig

    response = client.get(f"/api/v1/assistant/tools/{turn}/active_alerts")

    assert response.status_code == 200
    assert response.json() == {"alerts": ["CO₂ alto en el laboratorio"]}


def test_the_active_alerts_are_refused_outside_a_turn(rig) -> None:  # type: ignore[no-untyped-def]
    client, log, turn = rig
    log.close(turn)

    assert client.get(f"/api/v1/assistant/tools/{turn}/active_alerts").status_code == 404


def test_the_tools_can_only_read_nothing_here_changes_an_alert() -> None:
    router = build_router(
        log=RetrievalLog(),
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        alerts=FakeAlerts(),
    )

    routes = {(method, route.path) for route in router.routes for method in route.methods}  # type: ignore[attr-defined]

    assert routes == {
        ("POST", "/api/v1/assistant/tools/{turn_id}/search_passages"),
        ("GET", "/api/v1/assistant/tools/{turn_id}/active_alerts"),
    }
