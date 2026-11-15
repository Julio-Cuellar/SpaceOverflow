"""GraphQL de Nave e incidencias con la simulación real: escenario → ticket → zona en rojo."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from spaceapp.interfaces.graphql.context import Context
from spaceapp.interfaces.graphql.schema import schema
from spaceapp.main import build_facility, build_registry, build_services
from spaceapp.platform.outbox import OutboxRelay
from tests.integration.graphql.test_schema import CATALOG, LAYOUT, SETTINGS, World

pytestmark = pytest.mark.integration


class ShipWorld(World):
    def __init__(self, sf: Any) -> None:
        super().__init__(sf)
        self.facility = build_facility(SETTINGS, sf)
        self.relay = OutboxRelay(
            sf, build_registry(SETTINGS, CATALOG, self.knowledge, facility=self.facility)
        )
        self.ctx = Context(
            services=build_services(SETTINGS, sf, CATALOG, self.knowledge, self.facility)
        )

    async def gql_raw(self, query: str, **variables: Any) -> Any:
        return await schema.execute(query, variable_values=variables, context_value=self.ctx)


@pytest.fixture
def ship_world(session_factory: Any) -> ShipWorld:
    return ShipWorld(session_factory)


SHIP = "{ ship { code name zones { id code name status openIncidents layout { x y w h } } } }"
INCIDENTS = """query($status: IncidentStatus) { incidents(first: 10, status: $status) {
  nodes { id title severity status source typeKey valuesNormal zoneId
          type { key categoryName detection } updates { kind note } }
  pageInfo { hasNextPage } } }"""
RESULT = """__typename
  ... on IncidentPayload { alreadyDone incident { id status severity source } }
  ... on IncidentError { code message }"""


async def test_the_ship_lists_the_ten_zones_of_the_plan_in_normal(ship_world: ShipWorld) -> None:
    ship = (await ship_world.gql(SHIP))["ship"]
    assert ship["code"] == "nave-transito" and len(ship["zones"]) == 10
    assert {z["status"] for z in ship["zones"]} == {"NORMAL"}
    lab = next(z for z in ship["zones"] if z["code"] == "lab")
    assert lab["id"] == str(LAYOUT.zone_id("lab")), "las zonas de Nave y de Telemetría coinciden"
    assert lab["layout"] == {"x": 384.0, "y": 56.0, "w": 170.0, "h": 104.0}


async def test_an_unknown_habitat_has_no_ship(ship_world: ShipWorld) -> None:
    assert (await ship_world.gql('{ ship(habitatId: "base-lunar") { code } }'))["ship"] is None


async def test_a_co2_scenario_opens_a_ticket_and_paints_the_lab(ship_world: ShipWorld) -> None:
    await ship_world.run("co2_slow", "lab", 150, 330)
    zones = {z["code"]: z for z in (await ship_world.gql(SHIP))["ship"]["zones"]}
    assert zones["lab"]["status"] == "ALERTA" and zones["lab"]["openIncidents"] == 1
    assert zones["eng"]["status"] == "NORMAL"
    [ticket] = (await ship_world.gql(INCIDENTS))["incidents"]["nodes"]
    assert (ticket["title"], ticket["severity"], ticket["source"]) == (
        "CO₂ alto",
        "ALERTA",
        "ALERTA",
    )
    assert ticket["zoneId"] == zones["lab"]["id"]
    assert ticket["type"] == {
        "key": "co2_high",
        "categoryName": "Atmósfera y soporte vital",
        "detection": "AUTO",
    }
    assert ticket["updates"][0]["kind"] == "opened"

    blocked = (
        await ship_world.gql(
            f"mutation($id: ID!) {{ resolveIncident(id: $id) {{ {RESULT} }} }}", id=ticket["id"]
        )
    )["resolveIncident"]
    assert blocked["__typename"] == "IncidentError" and blocked["code"] == "ACTIVE_ALERTS"

    ack = (
        await ship_world.gql(
            f"mutation($id: ID!) {{ acknowledgeIncident(id: $id) {{ {RESULT} }} }}", id=ticket["id"]
        )
    )["acknowledgeIncident"]
    assert ack["incident"]["status"] == "RECONOCIDA" and ack["alreadyDone"] is False


async def test_the_crew_reports_an_incident_by_category_and_type(ship_world: ShipWorld) -> None:
    fire = (
        await ship_world.gql(
            '{ incidentTypes(category: "fire") { key detection defaultSeverity } }'
        )
    )["incidentTypes"]
    assert [t["key"] for t in fire] == ["smoke_fire", "burning_smell", "suppression_failure"]
    assert len((await ship_world.gql("{ incidentTypes { key } }"))["incidentTypes"]) == 61

    galley = str(LAYOUT.zone_id("galley"))
    report = f"""mutation($z: ID!, $t: String!, $s: Severity) {{
      reportIncident(zoneId: $z, typeKey: $t, severity: $s) {{ {RESULT} }} }}"""
    got = (await ship_world.gql(report, z=galley, t="burning_smell"))["reportIncident"]
    assert got["incident"]["source"] == "MANUAL" and got["incident"]["severity"] == "ALERTA"
    zones = {z["code"]: z for z in (await ship_world.gql(SHIP))["ship"]["zones"]}
    assert zones["galley"]["status"] == "ALERTA"

    done = (
        await ship_world.gql(
            f'mutation($id: ID!) {{ resolveIncident(id: $id, note: "listo") {{ {RESULT} }} }}',
            id=got["incident"]["id"],
        )
    )["resolveIncident"]
    assert done["incident"]["status"] == "RESUELTA"
    zones = {z["code"]: z for z in (await ship_world.gql(SHIP))["ship"]["zones"]}
    assert zones["galley"]["status"] == "NORMAL"


@pytest.mark.parametrize(
    ("variables", "code"),
    [
        ({"z": str(uuid4()), "t": "burning_smell"}, "UNKNOWN_ZONE"),
        ({"z": "no-es-uuid", "t": "burning_smell"}, "UNKNOWN_ZONE"),
        ({"t": "nope"}, "UNKNOWN_TYPE"),
        ({"t": "burning_smell", "s": "NORMAL"}, "INVALID_SEVERITY"),
    ],
)
async def test_bad_reports_are_typed_errors(
    ship_world: ShipWorld, variables: dict[str, Any], code: str
) -> None:
    variables.setdefault("z", str(LAYOUT.zone_id("lab")))
    report = f"""mutation($z: ID!, $t: String!, $s: Severity) {{
      reportIncident(zoneId: $z, typeKey: $t, severity: $s) {{ {RESULT} }} }}"""
    got = (await ship_world.gql(report, **variables))["reportIncident"]
    assert got["__typename"] == "IncidentError" and got["code"] == code
