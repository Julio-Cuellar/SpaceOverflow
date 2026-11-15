"""Seeds a mission end to end into the database, so the console shows data like its demo mode.

It is composition, not a module: it replays a simulated history through the app's own use cases
(telemetry, rules, alerts, incidents, tasks, Ground plan), so every row is the one the running
system would have written. Nothing is inserted behind the modules' back, and everything keeps its
origin label (SIMULATED readings, DEMO recommendations).

    python -m spaceapp.devtools.seed_mission --reset        # about a minute

The history ends now: three hours of nominal air with a slow CO₂ drift in the laboratory that the
rules turn into an alert, the incident and the follow-up tasks that come from it, one more incident
reported by hand, a crew task, and a Ground plan that was delivered and confirmed. Run the API
afterwards with `SPACEAPP_SIMULATOR_AUTOSTART=false` to keep that state on screen.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.interfaces.graphql.context import Context
from spaceapp.interfaces.graphql.schema import schema
from spaceapp.main import create_app, get_services, get_simulation
from spaceapp.platform.config import Settings
from spaceapp.platform.outbox import outbox_stats

SCHEMAS = ("platform", "monitoring", "telemetry", "facility", "engagement", "groundlink")
HABITAT = "transit-ship"
STEP_S = 30
# The CO₂ drift starts this long before the end of the history and is slow on purpose: at speed
# 0.02 the laboratory needs about twenty minutes to approach its target.
DRIFT_AFTER = timedelta(minutes=105)
DRIFT_SPEED = 0.02

SHIP = "query($h: ID!) { ship(habitatId: $h) { zones { id code name } } }"
ALERTS = "query { alerts(first: 50) { nodes { id ruleKey zoneId severity status raisedAt } } }"
INCIDENTS = (
    "query { incidents(first: 50) { nodes { id code title status source severity zoneId } } }"
)
TASKS = (
    "query($day: Date!) { tasks(day: $day) { id kind origin title status dueAt sourceAlertId } }"
)
GROUND = "query { groundControl { appliedVersion published { version stage } } }"
REPORT = """mutation($zone: ID!, $type: String!, $description: String!) {
  reportIncident(zoneId: $zone, typeKey: $type, description: $description) {
    __typename ... on IncidentError { code message } } }"""
ACK_INCIDENT = """mutation($id: ID!) {
  acknowledgeIncident(id: $id) { __typename ... on IncidentError { code message } } }"""
COMPLETE = """mutation($id: ID!, $effective: Boolean) {
  completeTask(id: $id, effective: $effective) { __typename ... on TaskError { code message } } }"""
BLOCK = """mutation($id: ID!, $reason: String!) {
  blockTask(id: $id, reason: $reason) { __typename ... on TaskError { code message } } }"""
CREATE_TASK = """mutation($title: String!, $due: DateTime) {
  createTask(kind: HEALTH, title: $title, dueAt: $due) {
    __typename ... on TaskError { code message } } }"""
SAVE_TEMPLATE = """mutation($title: String!, $kind: TaskKind!, $zone: String, $recurrence: String) {
  saveGroundTemplate(title: $title, kind: $kind, zoneCode: $zone, recurrence: $recurrence) {
    __typename ... on GroundError { code message } } }"""
PUBLISH = "mutation { publishGroundPlan { __typename ... on GroundError { code message } } }"
SET_LINK = """mutation($delay: Float) {
  setGroundLink(online: true, delaySeconds: $delay) { __typename } }"""


class SeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class Summary:
    readings: int
    alerts: list[str]
    incidents: list[str]
    tasks: int
    plan: str


async def reset(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Empties the tables of every module. Development only: it never runs without `--reset`."""
    async with session_factory() as session, session.begin():
        names = (
            await session.execute(
                text(
                    "SELECT format('%I.%I', schemaname, tablename) FROM pg_tables "
                    "WHERE schemaname = ANY(CAST(:s AS text[])) "
                    "AND tablename NOT LIKE 'alembic_version%'"
                ),
                {"s": list(SCHEMAS)},
            )
        ).scalars()
        await session.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))


async def has_history(session_factory: async_sessionmaker[AsyncSession]) -> bool:
    async with session_factory() as session:
        count = (await session.execute(text("SELECT count(*) FROM telemetry.reading"))).scalar_one()
    return bool(count)


async def drained(
    session_factory: async_sessionmaker[AsyncSession], limit_s: float = 180.0
) -> None:
    """Waits until the relay has delivered every event."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    while loop.time() - start < limit_s:
        async with session_factory() as session:
            stats = await outbox_stats(session)
        if stats.pending == 0:
            return
        await asyncio.sleep(0.1)
    raise SeedError("the relay did not deliver every event in time")


class Gql:
    """Runs GraphQL operations in process, with the same services the API uses."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    async def run(self, document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await schema.execute(
            document,
            variable_values=variables,
            context_value=Context(get_services(self._app)),
        )
        if result.errors:
            raise SeedError("; ".join(str(e) for e in result.errors))
        return result.data or {}

    async def command(self, document: str, variables: dict[str, Any]) -> None:
        """A mutation that answers with a typed error instead of raising."""
        data = await self.run(document, variables)
        (payload,) = data.values()
        if payload["__typename"].endswith("Error"):
            raise SeedError(f"{payload['code']}: {payload['message']}")


async def replay_telemetry(
    app: FastAPI,
    start: datetime,
    end: datetime,
    *,
    on_progress: Callable[[str], None] = lambda _: None,
) -> int:
    """Replays the simulator on a fake clock, one tick every `STEP_S` seconds."""
    sim = get_simulation(app)
    await sim.ensure_sensors()
    drift_at = end - DRIFT_AFTER
    started = False
    accepted = 0
    now = start
    while now <= end:
        if not started and now >= drift_at:
            await sim.start_scenario("co2_slow", "lab", speed=DRIFT_SPEED, now=now)
            started = True
        accepted += (await sim.tick(now)).accepted
        now += timedelta(seconds=STEP_S)
        if int((now - start).total_seconds()) % 1800 == 0:
            on_progress(f"  history up to {now:%H:%M}")
    return accepted


async def seed_incidents(gql: Gql, zones: dict[str, str]) -> None:
    """The alert opens its own incident; one more is reported by hand and acknowledged."""
    await gql.command(
        REPORT,
        {
            "zone": zones["crew"],
            "type": "loose_cargo",
            "description": "The equipment locker latch does not close. Inspect it with the "
            "applicable mission procedure.",
        },
    )
    incidents = (await gql.run(INCIDENTS))["incidents"]["nodes"]
    manual = next(i for i in incidents if i["source"] == "MANUAL")
    await gql.command(ACK_INCIDENT, {"id": manual["id"]})


async def seed_tasks(gql: Gql, now: datetime) -> None:
    """The day's routine: the first task done, one blocked with its reason and one crew task."""
    day = now.date().isoformat()
    tasks = (await gql.run(TASKS, {"day": day}))["tasks"]
    routine = sorted(
        (t for t in tasks if t["origin"] == "SYSTEM" and t["sourceAlertId"] is None),
        key=lambda t: t["dueAt"],
    )
    if routine:
        await gql.command(COMPLETE, {"id": routine[0]["id"], "effective": True})
    if len(routine) > 3:
        await gql.command(BLOCK, {"id": routine[3]["id"], "reason": "Waiting for the spare part"})
    due = (now + timedelta(hours=1)).replace(minute=0, second=0)
    await gql.command(
        CREATE_TASK, {"title": "Complete personal wellness log", "due": due.isoformat()}
    )


async def seed_ground_plan(
    gql: Gql, session_factory: async_sessionmaker[AsyncSession], *, limit_s: float = 60.0
) -> str:
    """Ground drafts and publishes a plan; the link delivers it and the ship confirms it."""
    await gql.run(SET_LINK, {"delay": 1.0})
    await gql.command(
        SAVE_TEMPLATE,
        {"title": "Daily mobility routine", "kind": "HEALTH", "zone": "gym", "recurrence": "DAILY"},
    )
    await gql.command(
        SAVE_TEMPLATE,
        {
            "title": "Inspect habitat air filters",
            "kind": "SHIP",
            "zone": "lab",
            "recurrence": "DAILY",
        },
    )
    await gql.command(PUBLISH, {})
    loop = asyncio.get_running_loop()
    start = loop.time()
    while loop.time() - start < limit_s:
        await drained(session_factory)
        view = (await gql.run(GROUND))["groundControl"]
        published = view["published"]
        if published and published["stage"] == "CONFIRMED":
            return f"v{published['version']} CONFIRMED"
        await asyncio.sleep(0.5)
    raise SeedError("the Ground plan was not confirmed in time")


async def seed(
    settings: Settings,
    *,
    hours: float = 3.0,
    clean: bool = False,
    now: datetime | None = None,
    on_progress: Callable[[str], None] = lambda _: None,
) -> Summary:
    end = (now or datetime.now(UTC)).replace(microsecond=0)
    start = end - timedelta(hours=hours)
    app = create_app(settings.model_copy(update={"relay_enabled": True}))
    async with app.router.lifespan_context(app):
        sf: async_sessionmaker[AsyncSession] = app.state.session_factory
        if clean:
            on_progress("Emptying the database")
            await reset(sf)
        elif await has_history(sf):
            raise SeedError("the database already has readings; run with --reset to replace them")
        gql = Gql(app)
        on_progress("Habitat map")
        ship = (await gql.run(SHIP, {"h": HABITAT}))["ship"]
        zones = {z["code"]: z["id"] for z in ship["zones"]}
        on_progress(f"Replaying {hours:g} h of telemetry")
        readings = await replay_telemetry(app, start, end, on_progress=on_progress)
        await drained(sf)
        on_progress("Incidents")
        await seed_incidents(gql, zones)
        on_progress("Tasks")
        await seed_tasks(gql, end)
        on_progress("Ground plan")
        plan = await seed_ground_plan(gql, sf)
        await drained(sf)
        alerts = [
            f"{a['ruleKey']} {a['severity']} {a['status']}"
            for a in (await gql.run(ALERTS))["alerts"]["nodes"]
        ]
        incidents = [
            f"{i['code']} {i['title']} {i['status']}"
            for i in (await gql.run(INCIDENTS))["incidents"]["nodes"]
        ]
        tasks = len((await gql.run(TASKS, {"day": end.date().isoformat()}))["tasks"])
    return Summary(readings, alerts, incidents, tasks, plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seeds a mission end to end into the database.")
    parser.add_argument("--hours", type=float, default=3.0, help="history to replay, default 3")
    parser.add_argument("--reset", action="store_true", help="empty the module tables first")
    args = parser.parse_args(argv)
    try:
        summary = asyncio.run(
            seed(Settings(), hours=args.hours, clean=args.reset, on_progress=print)
        )
    except SeedError as error:
        print(f"Seed failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary.__dict__, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
