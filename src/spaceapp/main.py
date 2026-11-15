"""Composition root: this is where adapters are chosen according to the profile."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strawberry.fastapi import GraphQLRouter

from spaceapp.interfaces.graphql.context import Context, Services
from spaceapp.interfaces.graphql.schema import schema
from spaceapp.interfaces.rest.admin import build_router as admin_router
from spaceapp.modules.engagement.adapters.inbound.events import register_engagement
from spaceapp.modules.engagement.adapters.outbound.json_data import load_system_templates
from spaceapp.modules.engagement.adapters.outbound.sql import SqlEngagementRepository
from spaceapp.modules.engagement.application.service import EngagementService
from spaceapp.modules.engagement.facade import GroundTemplateQuery, TaskQuery
from spaceapp.modules.facility.adapters.inbound.events import register_facility
from spaceapp.modules.facility.adapters.outbound.json_data import (
    load_catalog as load_incident_types,
)
from spaceapp.modules.facility.adapters.outbound.json_data import load_plan
from spaceapp.modules.facility.adapters.outbound.sql import SqlFacilityRepository
from spaceapp.modules.facility.application.service import FacilityService
from spaceapp.modules.facility.facade import IncidentQuery, ShipQuery
from spaceapp.modules.facility.ports import ActiveAlertsSource, ZoneAlert
from spaceapp.modules.groundlink.adapters.inbound.events import register_groundlink
from spaceapp.modules.groundlink.adapters.inbound.rest import build_router as groundlink_router
from spaceapp.modules.groundlink.adapters.outbound.sql import SqlGroundlinkRepository
from spaceapp.modules.groundlink.application.ground import GroundControl, ship_template
from spaceapp.modules.groundlink.application.receiver import PlanReceiver
from spaceapp.modules.groundlink.domain.plans import ShipTemplate
from spaceapp.modules.groundlink.ports import Schedule
from spaceapp.modules.knowledge.adapters.inbound.events import register_knowledge
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import (
    HandleAlertRaised,
    build_recommendation,
)
from spaceapp.modules.knowledge.domain.model import Recommendation, UnknownRuleError
from spaceapp.modules.knowledge.facade import KnowledgeQuery
from spaceapp.modules.monitoring.adapters.inbound.events import register_monitoring
from spaceapp.modules.monitoring.adapters.inbound.rest import build_router as monitoring_router
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.adapters.outbound.telemetry_readings import TelemetryReadings
from spaceapp.modules.monitoring.application.acknowledge_alert import AckResult, acknowledge_alert
from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.modules.monitoring.domain.rules import RuleCatalog
from spaceapp.modules.monitoring.facade import ActiveAlertsQuery, AlertReadQuery, RuleQuery
from spaceapp.modules.realtime.adapters.inbound.events import RealtimeEvents, register_realtime
from spaceapp.modules.realtime.adapters.inbound.ws import build_router as ws_router
from spaceapp.modules.realtime.adapters.outbound.sql import SqlOutboxReplay, seq_of
from spaceapp.modules.realtime.application.hub import Hub
from spaceapp.modules.realtime.domain.messages import WsMessage
from spaceapp.modules.telemetry.adapters.inbound.events import register_telemetry
from spaceapp.modules.telemetry.adapters.inbound.rest import build_router as telemetry_router
from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.rollup import RecomputeRollup
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.modules.telemetry.facade import TelemetryViews
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.config import Settings
from spaceapp.platform.db import make_engine, make_session_factory
from spaceapp.platform.ids import stable_uuid, zone_id
from spaceapp.platform.outbox import OutboxRelay, OutboxStats, outbox_stats
from spaceapp.platform.profiles import Profile

DEV_PROFILES = (Profile.DEV1, Profile.DEV2)

# Until profile selection exists, actions are signed by a demo crew member.
DEMO_CREW_MEMBER = stable_uuid("crew", "demo")


def _with_session[T](factory: Callable[[AsyncSession], T]) -> Callable[[AsyncSession | None], T]:
    """SQL adapters need the handler session; in-memory ones do not."""

    def build(session: AsyncSession | None) -> T:
        if session is None:
            raise RuntimeError("this adapter needs the outbox relay session")
        return factory(session)

    return build


@dataclass(frozen=True)
class KnowledgeWiring:
    """Dev B Knowledge with the demo source (everything it says is labelled DEMO)."""

    source: DemoKnowledgeSource
    recommendations: InMemoryRecommendations
    handler: HandleAlertRaised

    def recommendation_for(self, alert_id: UUID, rule_key: str) -> Recommendation | None:
        """The stored recommendation or, after a restart, the one the rule gives again.

        The recommendation is a pure function of the alert and its rule, so alerts that are in
        the database keep theirs even though the store is in memory.
        """
        stored = next((r for r in self.recommendations.all() if r.alert_id == alert_id), None)
        if stored is not None:
            return stored
        try:
            return build_recommendation(self.source, alert_id, rule_key)
        except UnknownRuleError:
            return None


def build_knowledge(settings: Settings) -> KnowledgeWiring:
    source = DemoKnowledgeSource.from_file(settings.knowledge_catalog_path)
    recommendations = InMemoryRecommendations()
    handler = HandleAlertRaised(
        source=source, recommendations=recommendations, inbox=InMemoryInbox()
    )
    return KnowledgeWiring(source, recommendations, handler)


def _active_alerts(session_factory: async_sessionmaker[AsyncSession]) -> ActiveAlertsSource:
    query = ActiveAlertsQuery(session_factory)

    async def read(habitat_id: UUID) -> list[ZoneAlert]:
        return [
            ZoneAlert(a.alert_id, a.zone_id, a.rule_key, a.severity, a.raised_at)
            for a in await query.list(habitat_id=habitat_id)
            if a.zone_id is not None
        ]

    return read


def build_facility(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> FacilityService:
    return FacilityService(
        load_plan(settings.facility_plan_path),
        load_incident_types(settings.incident_types_path),
        session_factory,
        SqlFacilityRepository,
        _active_alerts(session_factory),
    )


def build_engagement(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    facility: FacilityService,
    knowledge: KnowledgeWiring,
) -> EngagementService:
    plan = facility.plan

    def action_title(key: str) -> str | None:
        action = knowledge.source.action(key)
        return action.title if action else None

    return EngagementService(
        session_factory,
        SqlEngagementRepository,
        system_templates=load_system_templates(settings.engagement_templates_path),
        zone_codes={z.code for z in plan.zones},
        zone_id_of=lambda code: zone_id(plan.habitat_code, code),
        crew_member=DEMO_CREW_MEMBER,
        habitat_id=plan.habitat_id,
        action_title=action_title,
    )


@dataclass(frozen=True)
class GroundlinkWiring:
    receiver: PlanReceiver
    ground: GroundControl


def build_groundlink(
    session_factory: async_sessionmaker[AsyncSession], habitat_id: UUID, schedule: Schedule
) -> GroundlinkWiring:
    templates = GroundTemplateQuery(session_factory)

    async def ship_templates() -> list[ShipTemplate]:
        return [
            ship_template(t.template_id, t.title, t.kind, t.task_status, t.blocked_reason)
            for t in await templates.list()
            if t.active
        ]

    receiver = PlanReceiver(session_factory, SqlGroundlinkRepository, habitat_id)
    ground = GroundControl(
        session_factory, SqlGroundlinkRepository, receiver, ship_templates, schedule, habitat_id
    )
    return GroundlinkWiring(receiver, ground)


def background_schedule(tasks: set[asyncio.Task[None]]) -> Schedule:
    """Deferred delivery of the simulated link: waits out the delay and runs in the background."""

    def schedule(delay_s: float, job: Callable[[], Awaitable[None]]) -> None:
        async def run() -> None:
            await asyncio.sleep(delay_s)
            await job()

        task = asyncio.get_running_loop().create_task(run())
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    return schedule


def build_registry(
    settings: Settings,
    catalog: RuleCatalog,
    knowledge: KnowledgeWiring | None = None,
    hub: Hub | None = None,
    facility: FacilityService | None = None,
    engagement: EngagementService | None = None,
    groundlink: GroundlinkWiring | None = None,
) -> SubscriptionRegistry:
    registry = SubscriptionRegistry()
    register_knowledge(registry, (knowledge or build_knowledge(settings)).handler)
    if facility is not None:
        register_facility(registry, facility)
    if engagement is not None:
        register_engagement(registry, engagement)
    if groundlink is not None:
        register_groundlink(registry, groundlink.receiver, groundlink.ground)
    if hub is not None:
        register_realtime(registry, RealtimeEvents(hub, seq_of))
    register_telemetry(registry, RecomputeRollup(SqlTelemetryRepository))
    register_monitoring(
        registry,
        EvaluateReadings(
            catalog,
            _with_session(TelemetryReadings),
            _with_session(SqlAlertRepository),
            window_scale=settings.rule_window_scale,
            hysteresis=settings.alert_hysteresis,
        ),
    )
    return registry


def build_services(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    catalog: RuleCatalog,
    knowledge: KnowledgeWiring,
    facility: FacilityService | None = None,
    engagement: EngagementService | None = None,
    groundlink: GroundlinkWiring | None = None,
) -> Services:
    async def acknowledge(alert_id: UUID, note: str | None) -> AckResult:
        return await acknowledge_alert(
            session_factory, SqlAlertRepository, alert_id, DEMO_CREW_MEMBER, note=note
        )

    async def read_outbox_stats() -> OutboxStats:
        async with session_factory() as session:
            return await outbox_stats(session)

    facility = facility or build_facility(settings, session_factory)
    engagement = engagement or build_engagement(settings, session_factory, facility, knowledge)
    groundlink = groundlink or build_groundlink(
        session_factory, facility.plan.habitat_id, background_schedule(set())
    )
    return Services(
        alerts=AlertReadQuery(session_factory),
        active_alerts=ActiveAlertsQuery(session_factory),
        rules=RuleQuery(catalog),
        telemetry=TelemetryViews(session_factory),
        knowledge=KnowledgeQuery(knowledge.source),
        recommendation_for=knowledge.recommendation_for,
        acknowledge=acknowledge,
        facility=facility,
        ship=ShipQuery(session_factory),
        incidents=IncidentQuery(session_factory),
        crew_member=DEMO_CREW_MEMBER,
        engagement=engagement,
        tasks=TaskQuery(session_factory),
        ground=groundlink.ground,
        outbox_stats=read_outbox_stats if settings.profile in DEV_PROFILES else None,
    )


def get_services(app: FastAPI) -> Services:
    if app.state.services is None:
        app.state.services = build_services(
            app.state.settings,
            app.state.session_factory,
            app.state.catalog,
            app.state.knowledge,
            get_facility(app),
            get_engagement(app),
            get_groundlink(app),
        )
    services: Services = app.state.services
    return services


def get_facility(app: FastAPI) -> FacilityService:
    if app.state.facility is None:
        app.state.facility = build_facility(app.state.settings, app.state.session_factory)
    facility: FacilityService = app.state.facility
    return facility


def get_engagement(app: FastAPI) -> EngagementService:
    if app.state.engagement is None:
        app.state.engagement = build_engagement(
            app.state.settings, app.state.session_factory, get_facility(app), app.state.knowledge
        )
    engagement: EngagementService = app.state.engagement
    return engagement


def get_groundlink(app: FastAPI) -> GroundlinkWiring:
    if app.state.groundlink is None:
        app.state.groundlink = build_groundlink(
            app.state.session_factory,
            get_facility(app).plan.habitat_id,
            background_schedule(app.state.background),
        )
    groundlink: GroundlinkWiring = app.state.groundlink
    return groundlink


class _AppReplay:
    """The outbox is read with the app session, which only exists once the app starts."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    async def after(self, after_id: int, limit: int) -> Sequence[WsMessage]:
        return await SqlOutboxReplay(self._app.state.session_factory).after(after_id, limit)


def get_simulation(app: FastAPI) -> SimulationService:
    if app.state.sim is None:
        settings: Settings = app.state.settings
        app.state.sim = SimulationService(
            app.state.session_factory,
            SqlTelemetryRepository,
            load_layout(settings.sim_layout_path),
            seed=settings.sim_seed,
        )
    sim: SimulationService = app.state.sim
    return sim


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        if app.state.session_factory is None:
            engine = make_engine(settings.database_url)
            app.state.session_factory = make_session_factory(engine)
        stop = asyncio.Event()
        app.state.relay_task = app.state.simulator_task = None
        if settings.relay_enabled:
            relay = OutboxRelay(
                app.state.session_factory,
                build_registry(
                    settings,
                    app.state.catalog,
                    app.state.knowledge,
                    app.state.hub,
                    get_facility(app),
                    get_engagement(app),
                    get_groundlink(app),
                ),
                listen_dsn=settings.database_url.replace("+asyncpg", ""),
            )
            app.state.relay_task = asyncio.create_task(relay.run_forever(stop))
        if settings.simulator_autostart:
            sim = get_simulation(app)
            await sim.ensure_sensors()
            app.state.simulator_task = asyncio.create_task(sim.run_forever(stop))
        yield
        stop.set()
        for task in (app.state.relay_task, app.state.simulator_task):
            if task is not None:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(task, timeout=5)
        if engine is not None:
            await engine.dispose()

    app = FastAPI(title="Health monitor for astronauts", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.catalog = load_catalog(settings.rules_path)
    app.state.knowledge = build_knowledge(settings)
    app.state.hub = Hub()
    app.state.services = None
    app.state.facility = None
    app.state.engagement = None
    app.state.groundlink = None
    app.state.background = set()
    app.state.sim = None
    app.state.relay_task = app.state.simulator_task = None
    app.include_router(monitoring_router(app.state.catalog))
    app.include_router(telemetry_router(get_simulation))

    async def graphql_context(request: Request) -> Context:
        return Context(get_services(request.app))

    app.include_router(GraphQLRouter(schema, context_getter=graphql_context), prefix="/graphql")
    app.include_router(ws_router(app.state.hub, _AppReplay(app)))

    def groundlink_services() -> tuple[PlanReceiver, GroundControl]:
        wiring = get_groundlink(app)
        return wiring.receiver, wiring.ground

    app.include_router(groundlink_router(groundlink_services))
    if settings.profile in DEV_PROFILES:
        app.include_router(admin_router(lambda: app.state.session_factory))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "profile": settings.profile.value}

    @app.get("/ready", response_model=None)
    async def ready() -> JSONResponse | dict[str, object]:
        sf = app.state.session_factory
        try:
            async with sf() as session:
                stats = await outbox_stats(session)
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {
            "status": "ok",
            "outbox": {
                "pending": stats.pending,
                "dead": stats.dead,
                "oldest_pending_age_s": stats.oldest_pending_age_s,
            },
        }

    return app
