"""El workflow de n8n es dato versionado: se comprueba su forma sin necesitar n8n."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spaceapp.modules.assistant.adapters.inbound.rest import build_router
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog

N8N = Path(__file__).resolve().parents[2] / "n8n"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    [wf] = json.loads((N8N / "workflows" / "space-apps-asistente.json").read_text("utf-8"))
    return wf  # type: ignore[no-any-return]


def node(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    return next(n for n in workflow["nodes"] if n["name"] == name)


def test_every_connection_points_to_a_node_that_exists(workflow: dict[str, Any]) -> None:
    names = {n["name"] for n in workflow["nodes"]}

    for source, kinds in workflow["connections"].items():
        assert source in names
        for branches in kinds.values():
            for branch in branches:
                for link in branch:
                    assert link["node"] in names


def test_the_agent_has_exactly_the_two_read_only_tools(workflow: dict[str, Any]) -> None:
    tools = [source for source, kinds in workflow["connections"].items() if "ai_tool" in kinds]

    assert sorted(tools) == ["active_alerts", "search_passages"]


def test_the_tool_urls_match_the_routes_the_backend_exposes(workflow: dict[str, Any]) -> None:
    router = build_router(log=RetrievalLog(), passages=None, alerts=None)  # type: ignore[arg-type]
    paths = {route.path.rsplit("/", 1)[1] for route in router.routes}  # type: ignore[attr-defined]

    for name in ("search_passages", "active_alerts"):
        assert node(workflow, name)["parameters"]["url"].rsplit("/", 1)[1] == name
        assert name in paths


def test_the_backend_address_lives_in_one_place_the_config_node(workflow: dict[str, Any]) -> None:
    config = {
        a["name"]: a["value"]
        for a in node(workflow, "Config")["parameters"]["assignments"]["assignments"]
    }
    others = json.dumps([n for n in workflow["nodes"] if n["name"] != "Config"])

    assert config["backend_url"].startswith("http")
    assert "host.docker.internal" not in others


def test_the_model_is_chosen_in_the_config_node(workflow: dict[str, Any]) -> None:
    config = {
        a["name"]: a["value"]
        for a in node(workflow, "Config")["parameters"]["assignments"]["assignments"]
    }

    assert config["model"]
    assert node(workflow, "Ollama Chat Model")["parameters"]["model"] == (
        "={{ $('Config').first().json.model }}"
    )


def test_n8n_does_not_store_what_the_crew_asks(workflow: dict[str, Any]) -> None:
    settings = workflow["settings"]

    assert settings["saveDataSuccessExecution"] == "none"
    assert settings["saveDataErrorExecution"] == "none"


def test_the_agent_rules_forbid_touching_alerts_and_inventing(workflow: dict[str, Any]) -> None:
    rules = node(workflow, "Agente")["parameters"]["options"]["systemMessage"]

    assert "search_passages" in rules
    assert "No tengo esa información en las fuentes cargadas." in rules
    assert "No puedes cambiar, reconocer ni resolver alertas" in rules


def test_the_credential_file_holds_no_secret() -> None:
    [credential] = json.loads((N8N / "credentials" / "ollama.json").read_text("utf-8"))

    assert set(credential["data"]) == {"baseUrl"}
