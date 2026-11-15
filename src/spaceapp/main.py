"""Composition root: aquí se eligen los adaptadores según el perfil."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable, Sequence
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
from spaceapp.modules.knowledge.adapters.inbound.events import register_knowledge
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.memory import (
    InMemoryInbox,
    InMemoryRecommendations,
)
from spaceapp.modules.knowledge.application.handle_alert_raised import HandleAlertRaised
from spaceapp.modules.knowledge.domain.model import Recommendation
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
from spaceapp.platform.ids import stable_uuid
from spaceapp.platform.outbox import OutboxRelay, OutboxStats, outbox_stats
from spaceapp.platform.profiles import Profile

DEV_PROFILES = (Profile.DEV1, Profile.DEV2)

# Hasta que haya selección de perfil, las acciones se firman con un tripulante de demostración.
DEMO_CREW_MEMBER = stable_uuid("crew", "demo")


def _with_session[T](factory: Callable[[AsyncSession], T]) -> Callable[[AsyncSession | None], T]:
    """Los adaptadores SQL necesitan la sesión del handler; en memoria no aplican."""

    def build(session: AsyncSession | None) -> T:
        if session is None:
            raise RuntimeError("este adaptador necesita la sesión del relay del outbox")
        return factory(session)

    return build


@dataclass(frozen=True)
class KnowledgeWiring:
    """Conocimiento de Dev B con la fuente de demostración (todo lo que dice se etiqueta DEMO)."""

    source: DemoKnowledgeSource
    recommendations: InMemoryRecommendations
    handler: HandleAlertRaised

    def recommendation_for(self, alert_id: UUID) -> Recommendation | None:
        return next((r for r in self.recommendations.all() if r.alert_id == alert_id), None)


def build_knowledge(settings: Settings) -> KnowledgeWiring:
    source = DemoKnowledgeSource.from_file(settings.knowledge_catalog_path)
    recommendations = InMemoryRecommendations()
    handler = HandleAlertRaised(
        source=source, recommendations=recommendations, inbox=InMemoryInbox()
    )
    return KnowledgeWiring(source, recommendations, handler)


def build_registry(
    settings: Settings,
    catalog: RuleCatalog,
    knowledge: KnowledgeWiring | None = None,
    hub: Hub | None = None,
) -> SubscriptionRegistry:
    registry = SubscriptionRegistry()
    register_knowledge(registry, (knowledge or build_knowledge(settings)).handler)
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
) -> Services:
    async def acknowledge(alert_id: UUID, note: str | None) -> AckResult:
        return await acknowledge_alert(
            session_factory, SqlAlertRepository, alert_id, DEMO_CREW_MEMBER, note=note
        )

    async def read_outbox_stats() -> OutboxStats:
        async with session_factory() as session:
            return await outbox_stats(session)

    return Services(
        alerts=AlertReadQuery(session_factory),
        active_alerts=ActiveAlertsQuery(session_factory),
        rules=RuleQuery(catalog),
        telemetry=TelemetryViews(session_factory),
        knowledge=KnowledgeQuery(knowledge.source),
        recommendation_for=knowledge.recommendation_for,
        acknowledge=acknowledge,
        outbox_stats=read_outbox_stats if settings.profile in DEV_PROFILES else None,
    )


def get_services(app: FastAPI) -> Services:
    if app.state.services is None:
        app.state.services = build_services(
            app.state.settings, app.state.session_factory, app.state.catalog, app.state.knowledge
        )
    services: Services = app.state.services
    return services


class _AppReplay:
    """El outbox se lee con la sesión de la app, que existe recién al arrancar."""

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
                build_registry(settings, app.state.catalog, app.state.knowledge, app.state.hub),
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

    app = FastAPI(title="Monitor de salud para astronautas", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.catalog = load_catalog(settings.rules_path)
    app.state.knowledge = build_knowledge(settings)
    app.state.hub = Hub()
    app.state.services = None
    app.state.sim = None
    app.state.relay_task = app.state.simulator_task = None
    app.include_router(monitoring_router(app.state.catalog))
    app.include_router(telemetry_router(get_simulation))

    async def graphql_context(request: Request) -> Context:
        return Context(get_services(request.app))

    app.include_router(GraphQLRouter(schema, context_getter=graphql_context), prefix="/graphql")
    app.include_router(ws_router(app.state.hub, _AppReplay(app)))
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
