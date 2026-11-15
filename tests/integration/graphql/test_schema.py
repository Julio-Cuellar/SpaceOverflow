"""GraphQL on a real PostgreSQL, with the data a simulation leaves behind."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.interfaces.graphql.context import Context
from spaceapp.interfaces.graphql.schema import schema
from spaceapp.main import build_knowledge, build_registry, build_services
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.platform.config import Settings
from spaceapp.platform.outbox import OutboxRelay
from tests.integration.telemetry.conftest import T0

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
SETTINGS = Settings(rule_window_scale=1 / 60)
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
LAYOUT = load_layout(ROOT / "data" / "telemetry" / "sim_layout.json")


class World:
    def __init__(self, sf: Any) -> None:
        self.sf = sf
        self.knowledge = build_knowledge(SETTINGS)
        self.relay = OutboxRelay(sf, build_registry(SETTINGS, CATALOG, self.knowledge))
        self.sim = SimulationService(sf, SqlTelemetryRepository, LAYOUT, seed=7)
        self.ctx = Context(services=build_services(SETTINGS, sf, CATALOG, self.knowledge))

    async def drain(self) -> None:
        while await self.relay.run_once():
            pass

    async def run(self, scenario: str | None, zone: str, start_at: int, until: int) -> None:
        await self.sim.ensure_sensors()
        for step in range(0, until + 1, 5):
            now = T0 + timedelta(seconds=step)
            if scenario and step == start_at:
                await self.sim.start_scenario(scenario, zone, now=now)
            await self.sim.tick(now)
            await self.drain()

    async def gql(self, query: str, **variables: Any) -> dict[str, Any]:
        result = await schema.execute(query, variable_values=variables, context_value=self.ctx)
        assert result.errors is None, result.errors
        assert result.data is not None
        return result.data


@pytest.fixture
def world(session_factory: Any) -> World:
    return World(session_factory)


DASHBOARD = """
query($h: ID!) { dashboard(habitatId: $h) {
  habitatId globalSeverity
  vitals { key label value unit domain severity evidenceState origin zoneId }
} }
"""


async def test_an_empty_habitat_is_normal_with_no_vitals(world: World) -> None:
    data = await world.gql(DASHBOARD, h="transit-ship")
    assert data["dashboard"]["globalSeverity"] == "NORMAL"
    assert data["dashboard"]["vitals"] == []


async def test_a_normal_run_shows_every_vital_as_normal_and_simulated(world: World) -> None:
    await world.run(None, "lab", -1, 30)
    d = (await world.gql(DASHBOARD, h="transit-ship"))["dashboard"]
    assert d["globalSeverity"] == "NORMAL"
    keys = {v["key"] for v in d["vitals"]}
    assert keys == {"pressure_kpa", "o2_pct", "co2_mmhg", "temperature_c", "humidity_pct", "pio2"}
    assert all(v["severity"] == "NORMAL" and v["domain"] == "cabin" for v in d["vitals"])
    assert {v["origin"] for v in d["vitals"] if v["key"] != "pio2"} == {"SIMULATED"}
    pio2 = next(v for v in d["vitals"] if v["key"] == "pio2")
    assert pio2["unit"] == "mmHg" and 140 < pio2["value"] < 170


async def test_the_habitat_can_be_given_as_its_uuid_or_its_code(world: World) -> None:
    await world.run(None, "lab", -1, 10)
    by_code = await world.gql(DASHBOARD, h="transit-ship")
    by_uuid = await world.gql(DASHBOARD, h=by_code["dashboard"]["habitatId"])
    assert by_code == by_uuid


async def test_an_active_alert_colors_its_vital_and_the_global_state(world: World) -> None:
    await world.run("co2_slow", "lab", 150, 330)
    d = (await world.gql(DASHBOARD, h="transit-ship"))["dashboard"]
    assert d["globalSeverity"] == "ALERT"
    co2 = next(v for v in d["vitals"] if v["key"] == "co2_mmhg")
    assert co2["severity"] == "ALERT" and co2["evidenceState"] == "VERIFIED"
    assert co2["zoneId"] is not None
    assert next(v for v in d["vitals"] if v["key"] == "temperature_c")["severity"] == "NORMAL"


ALERTS = """
query($first: Int!, $after: String, $status: AlertStatus) {
  alerts(first: $first, after: $after, status: $status) {
    nodes { id ruleKey severity status evidenceState zoneId }
    pageInfo { hasNextPage endCursor }
  }
}
"""


async def test_alerts_are_paginated_by_cursor_and_filterable(world: World) -> None:
    await world.run("co2_slow", "lab", 150, 330)
    page1 = (await world.gql(ALERTS, first=1))["alerts"]
    assert len(page1["nodes"]) == 1 and page1["pageInfo"]["hasNextPage"] is True
    page2 = (await world.gql(ALERTS, first=10, after=page1["pageInfo"]["endCursor"]))["alerts"]
    ids = [n["id"] for n in page1["nodes"] + page2["nodes"]]
    assert len(ids) == len(set(ids)) >= 3 and page2["pageInfo"]["hasNextPage"] is False
    raised = (await world.gql(ALERTS, first=10, status="RAISED"))["alerts"]["nodes"]
    assert raised and all(n["status"] == "RAISED" for n in raised)
    # The pre-alert (Attention) resolves when it is replaced by the alert (`supersedes`).
    resolved = (await world.gql(ALERTS, first=10, status="RESOLVED"))["alerts"]["nodes"]
    assert resolved and all(n["status"] == "RESOLVED" for n in resolved)
    assert {n["ruleKey"] for n in resolved}.isdisjoint({n["ruleKey"] for n in raised})


DETAIL = """
query($id: ID!) { alert(id: $id) {
  id ruleKey severity status causeHint evidenceState evidence
  rule { key sourceRequirement sourceDocument evidenceState }
  recommendation { id sourceKind body actions { key title } citations { documentCode excerpt evidenceState } }
} }
"""


async def test_an_alert_comes_with_its_rule_and_the_recommendation_with_citations(
    world: World,
) -> None:
    await world.run("co2_slow", "lab", 150, 330)
    nodes = (await world.gql(ALERTS, first=20))["alerts"]["nodes"]
    target = next(n for n in nodes if n["ruleKey"] == "env-co2-1h")
    a = (await world.gql(DETAIL, id=target["id"]))["alert"]
    assert a["rule"]["key"] == "env-co2-1h" and a["rule"]["sourceDocument"]
    assert a["causeHint"] == "ENVIRONMENT" and a["evidence"]["value"] > 0
    rec = a["recommendation"]
    assert rec is not None and rec["citations"], "every recommendation carries citations"
    assert rec["sourceKind"] == "DEMO"


async def test_an_unknown_alert_is_null(world: World) -> None:
    assert (await world.gql(DETAIL, id=str(uuid4())))["alert"] is None


async def test_the_rule_catalog_exposes_the_limit_to_draw_it(world: World) -> None:
    rules = (await world.gql("{ rules { key kind operator threshold unit windowS } }"))["rules"]
    by_key = {r["key"]: r for r in rules}
    assert by_key["env-co2-1h"] == {
        "key": "env-co2-1h",
        "kind": "threshold",
        "operator": ">",
        "threshold": 3.0,
        "unit": "mmHg",
        "windowS": 3600,
    }
    assert by_key["env-trend-co2"]["kind"] == "trend"
    assert all(r["operator"] in ("<", "<=", ">", ">=") and r["unit"] for r in rules)


async def test_the_rule_catalog_exposes_source_and_evidence_state(world: World) -> None:
    rules = (
        await world.gql("{ rules { key severity evidenceState sourceRequirement actionKey } }")
    )["rules"]
    assert len(rules) == 25
    assert {r["evidenceState"] for r in rules} <= {"VERIFIED", "TB", "DEMO"}
    assert all(r["sourceRequirement"] for r in rules)


async def test_zone_readings_return_the_series_of_a_zone(world: World) -> None:
    await world.run(None, "lab", -1, 180)
    zone = str(LAYOUT.zone_id("lab"))
    q = """query($z: ID!, $a: DateTime!, $b: DateTime!) {
      zoneReadings(zoneId: $z, metrics: ["co2_mmhg", "o2_pct"], from: $a, to: $b) {
        metric unit points { ts avg min max } } }"""
    got = (await world.gql(q, z=zone, a=T0.isoformat(), b=(T0 + timedelta(minutes=5)).isoformat()))[
        "zoneReadings"
    ]
    assert {s["metric"] for s in got} == {"co2_mmhg", "o2_pct"}
    co2 = next(s for s in got if s["metric"] == "co2_mmhg")
    assert co2["unit"] == "mmHg" and len(co2["points"]) >= 2
    assert all(p["min"] <= p["avg"] <= p["max"] for p in co2["points"])


async def test_zone_readings_can_return_raw_samples(world: World) -> None:
    await world.run(None, "lab", -1, 30)
    zone = str(LAYOUT.zone_id("lab"))
    q = """query($z: ID!, $a: DateTime!, $b: DateTime!) {
      zoneReadings(zoneId: $z, metrics: ["pressure_kpa"], from: $a, to: $b, resolution: RAW) {
        points { ts avg } } }"""
    pts = (await world.gql(q, z=zone, a=T0.isoformat(), b=(T0 + timedelta(minutes=1)).isoformat()))[
        "zoneReadings"
    ][0]["points"]
    # One sample per tick: the test advances the simulation in 5 s steps (0, 5, …, 30).
    assert [p["ts"][11:19] for p in pts] == [f"12:00:{s:02d}" for s in range(0, 31, 5)]
    assert all(isinstance(p["avg"], float) for p in pts)


async def test_knowledge_search_returns_cited_passages(world: World) -> None:
    got = (
        await world.gql(
            """{ knowledgeSearch(query: "carbon dioxide", k: 3) {
                 documentCode excerpt evidenceState } }"""
        )
    )["knowledgeSearch"]
    assert isinstance(got, list) and len(got) <= 3


ACK = """mutation($id: ID!, $note: String) { acknowledgeAlert(id: $id, note: $note) {
  __typename
  ... on AlertAcknowledgedPayload { alert { id status } alreadyAcknowledged }
  ... on AlertError { code message }
} }"""


async def test_acknowledging_is_idempotent_and_publishes_one_event(world: World) -> None:
    await world.run("co2_slow", "lab", 150, 330)
    target = (await world.gql(ALERTS, first=1, status="RAISED"))["alerts"]["nodes"][0]["id"]
    first = (await world.gql(ACK, id=target, note="enterado"))["acknowledgeAlert"]
    assert first["__typename"] == "AlertAcknowledgedPayload"
    assert first["alert"]["status"] == "ACKNOWLEDGED" and first["alreadyAcknowledged"] is False
    again = (await world.gql(ACK, id=target))["acknowledgeAlert"]
    assert again["alreadyAcknowledged"] is True
    async with world.sf() as s:
        n = (
            await s.execute(
                text(
                    "SELECT count(*) FROM platform.outbox_event WHERE type = 'monitoring.alert_acknowledged'"
                )
            )
        ).scalar_one()
    assert n == 1


async def test_acknowledging_an_unknown_alert_is_a_typed_error(world: World) -> None:
    got = (await world.gql(ACK, id=str(uuid4())))["acknowledgeAlert"]
    assert got == {"__typename": "AlertError", "code": "NOT_FOUND", "message": got["message"]}


async def test_acknowledging_a_resolved_alert_is_a_typed_error(world: World) -> None:
    await world.run("co2_slow", "lab", 150, 330)
    target = (await world.gql(ALERTS, first=1))["alerts"]["nodes"][0]["id"]
    async with world.sf() as s, s.begin():
        await s.execute(
            text(
                "UPDATE monitoring.alert SET status = 'resolved', resolved_at = now() WHERE id = :i"
            ),
            {"i": target},
        )
    got = (await world.gql(ACK, id=target))["acknowledgeAlert"]
    assert got["__typename"] == "AlertError" and got["code"] == "ALREADY_RESOLVED"
