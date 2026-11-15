"""Facility on real PostgreSQL: F4 acceptance criteria."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.facility.adapters.inbound.events import register_facility
from spaceapp.modules.facility.adapters.outbound.json_data import load_catalog, load_plan
from spaceapp.modules.facility.adapters.outbound.sql import SqlFacilityRepository
from spaceapp.modules.facility.application.service import Done, FacilityService, Failed
from spaceapp.modules.facility.facade import IncidentQuery, ShipQuery
from spaceapp.modules.facility.ports import ZoneAlert
from spaceapp.modules.monitoring.contracts import AlertRaised, AlertResolved
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.events import EventEnvelope
from spaceapp.platform.outbox import OutboxRelay, UnitOfWork

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
PLAN = load_plan(ROOT / "data" / "facility" / "plan.json")
CATALOG = load_catalog(ROOT / "data" / "facility" / "incident_types.json")
LAB = PLAN.zone("lab")
ENG = PLAN.zone("eng")
assert LAB is not None and ENG is not None
CREW = uuid4()
EVIDENCE = {"parameter": "ppco2", "value": 3.4, "unit": "mmHg", "operator": ">", "threshold": 3.0}


class World:
    def __init__(self, sf: Any, active: Sequence[ZoneAlert] = ()) -> None:
        self.sf = sf
        self.active = list(active)
        self.service = FacilityService(PLAN, CATALOG, sf, SqlFacilityRepository, self._active)
        registry = SubscriptionRegistry()
        register_facility(registry, self.service)
        self.relay = OutboxRelay(sf, registry)
        self.incidents = IncidentQuery(sf)

    async def _active(self, habitat_id: UUID) -> Sequence[ZoneAlert]:
        return self.active

    async def emit(self, payload: AlertRaised | AlertResolved) -> None:
        async with UnitOfWork(self.sf) as uow:
            await uow.publish(
                EventEnvelope.from_payload(
                    payload,
                    aggregate_type="alert",
                    aggregate_id=payload.alert_id,
                    partition_key="p",
                )
            )
        while await self.relay.run_once():
            pass

    async def raise_alert(self, zone: UUID, severity: str, rule: str = "env-co2-1h") -> UUID:
        alert_id = uuid4()
        await self.emit(
            AlertRaised(
                alert_id=alert_id, zone_id=zone, rule_key=rule, severity=severity, evidence=EVIDENCE
            )
        )
        return alert_id

    async def resolve_alert(self, alert_id: UUID) -> None:
        await self.emit(
            AlertResolved(alert_id=alert_id, resolved_at=datetime.now(UTC), duration_s=5)
        )

    async def zone_status(self, zone: UUID) -> str:
        async with self.sf() as s:
            return str(
                (
                    await s.execute(
                        text("SELECT status FROM facility.zone WHERE id = :z"), {"z": zone}
                    )
                ).scalar_one()
            )

    async def events(self, prefix: str = "facility.") -> list[str]:
        async with self.sf() as s:
            rows = await s.execute(
                text("SELECT type FROM platform.outbox_event WHERE type LIKE :p ORDER BY id"),
                {"p": prefix + "%"},
            )
            return [r[0] for r in rows]

    async def tickets(self) -> list[Any]:
        return (await self.incidents.page(50))[0]


@pytest.fixture
def world(session_factory: Any) -> World:
    return World(session_factory)


async def test_an_alert_opens_exactly_one_ticket_and_turns_the_zone_red(world: World) -> None:
    await world.raise_alert(LAB.id, "alert")
    [ticket] = await world.tickets()
    assert (ticket.zone_id, ticket.severity, ticket.status, ticket.source) == (
        LAB.id,
        "alert",
        "open",
        "ALERT",
    )
    assert ticket.type_key == "co2_high" and ticket.title == "High CO₂"
    assert ticket.description.startswith("High CO₂ in Laboratory: ppco2 = 3.4 mmHg")
    assert await world.zone_status(LAB.id) == "alert"
    assert await world.zone_status(ENG.id) == "normal"
    assert await world.events() == ["facility.incident_opened", "facility.zone_status_changed"]


async def test_a_second_alert_in_the_zone_does_not_open_another_ticket(world: World) -> None:
    await world.raise_alert(LAB.id, "alert")
    await world.raise_alert(LAB.id, "alert", rule="env-pio2-low")
    assert len(await world.tickets()) == 1
    assert await world.events() == ["facility.incident_opened", "facility.zone_status_changed"]
    [ticket] = await world.tickets()
    kinds = [u.kind for u in await world.incidents.updates(ticket.id)]
    assert kinds == ["opened", "alert"]


async def test_a_worse_alert_escalates_the_ticket_and_the_zone(world: World) -> None:
    await world.raise_alert(LAB.id, "alert")
    await world.raise_alert(LAB.id, "critical", rule="env-co2-crit")
    [ticket] = await world.tickets()
    assert ticket.severity == "critical" and await world.zone_status(LAB.id) == "critical"
    assert (await world.events())[-2:] == [
        "facility.incident_updated",
        "facility.zone_status_changed",
    ]


async def test_a_trend_colors_the_zone_but_opens_no_ticket(world: World) -> None:
    await world.raise_alert(LAB.id, "attention", rule="env-trend-co2")
    assert await world.tickets() == []
    assert await world.zone_status(LAB.id) == "attention"


async def test_an_automatic_ticket_cannot_be_resolved_while_values_are_out_of_range(
    world: World,
) -> None:
    alert = await world.raise_alert(LAB.id, "alert")
    [ticket] = await world.tickets()
    blocked = await world.service.resolve(ticket.id, CREW, "done")
    assert isinstance(blocked, Failed) and blocked.code == "ACTIVE_ALERTS"

    await world.resolve_alert(alert)
    still = await world.incidents.get(ticket.id)
    assert still is not None and still.status == "open", "the ticket does not close itself"
    assert still.values_normal_at is not None
    assert await world.zone_status(LAB.id) == "alert", "the open ticket keeps the color"

    assert await world.service.resolve(ticket.id, CREW, "filter replaced") == Done(ticket.id)
    assert await world.zone_status(LAB.id) == "normal"
    assert (await world.events())[-2:] == [
        "facility.incident_resolved",
        "facility.zone_status_changed",
    ]
    again = await world.service.resolve(ticket.id, CREW, None)
    assert isinstance(again, Failed) and again.code == "ALREADY_RESOLVED"


async def test_a_manual_report_opens_a_ticket_that_can_be_resolved_anytime(world: World) -> None:
    await world.raise_alert(ENG.id, "alert")
    got = await world.service.report(
        ENG.id, "burning_smell", CREW, description="Smells like burning"
    )
    assert isinstance(got, Done)
    manual = await world.incidents.get(got.incident_id)
    assert manual is not None and manual.source == "MANUAL" and manual.severity == "alert"
    assert manual.description == "Smells like burning"
    assert len(await world.tickets()) == 2, (
        "the manual ticket does not count as the zone's automatic one"
    )
    assert await world.service.resolve(got.incident_id, CREW, None) == Done(got.incident_id)


async def test_a_manual_report_takes_the_default_severity_and_can_raise_the_zone(
    world: World,
) -> None:
    got = await world.service.report(ENG.id, "hull_damage", CREW)
    assert isinstance(got, Done)
    assert await world.zone_status(ENG.id) == "critical"


async def test_reports_with_unknown_zone_or_type_are_typed_errors(world: World) -> None:
    zone = await world.service.report(uuid4(), "burning_smell", CREW)
    kind = await world.service.report(ENG.id, "nope", CREW)
    assert isinstance(zone, Failed) and zone.code == "UNKNOWN_ZONE"
    assert isinstance(kind, Failed) and kind.code == "UNKNOWN_TYPE"


async def test_acknowledging_is_idempotent(world: World) -> None:
    await world.raise_alert(LAB.id, "alert")
    [ticket] = await world.tickets()
    assert await world.service.acknowledge(ticket.id, CREW) == Done(ticket.id)
    assert await world.service.acknowledge(ticket.id, CREW) == Done(ticket.id, already=True)
    assert (await world.incidents.get(ticket.id)).status == "acknowledged"  # type: ignore[union-attr]
    assert (await world.events()).count("facility.incident_updated") == 1
    missing = await world.service.acknowledge(uuid4(), CREW)
    assert isinstance(missing, Failed) and missing.code == "NOT_FOUND"


async def test_restarting_rebuilds_the_zone_state_from_the_active_alerts(
    session_factory: Any,
) -> None:
    first = World(session_factory)
    await first.service.ensure_ready()
    assert await first.zone_status(LAB.id) == "normal"
    # On restart, Monitoring reports an active alert that Facility had not seen.
    active = [ZoneAlert(uuid4(), LAB.id, "env-co2-1h", "alert", datetime.now(UTC))]
    restarted = World(session_factory, active)
    await restarted.service.ensure_ready()
    assert await restarted.zone_status(LAB.id) == "alert"
    assert await restarted.zone_status(ENG.id) == "normal"


async def test_changing_the_plan_changes_the_zones_of_the_ship(session_factory: Any) -> None:
    smaller = replace(PLAN, zone_plans=PLAN.zone_plans[:3])
    service = FacilityService(smaller, CATALOG, session_factory, SqlFacilityRepository, _none)
    await service.ensure_ready()
    zones = await ShipQuery(session_factory).zones(smaller.habitat_id)
    assert [z.code for z in zones] == ["eng", "eclss", "lab"]
    assert all(z.status == "normal" and z.open_incidents == 0 for z in zones)
    assert zones[0].layout == {"x": 60, "y": 56, "w": 150, "h": 104}


async def _none(habitat_id: UUID) -> Sequence[ZoneAlert]:
    return []


async def test_tickets_get_a_sequential_readable_code_that_also_travels_in_the_event(
    world: World,
) -> None:
    await world.raise_alert(LAB.id, "alert")
    manual = await world.service.report(ENG.id, "burning_smell", CREW)
    assert isinstance(manual, Done)
    codes = {t.title: t.code for t in await world.tickets()}
    assert sorted(codes.values()) == ["INC-0001", "INC-0002"]
    assert codes["High CO₂"] == "INC-0001", "numbered in the order they are opened"
    async with world.sf() as s:
        payloads = (
            (
                await s.execute(
                    text(
                        "SELECT payload FROM platform.outbox_event WHERE type = 'facility.incident_opened' ORDER BY id"
                    )
                )
            )
            .scalars()
            .all()
        )
    sent = [p if isinstance(p, dict) else json.loads(p) for p in payloads]
    assert [p["code"] for p in sent] == ["INC-0001", "INC-0002"]
