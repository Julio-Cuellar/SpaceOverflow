"""Composition root: aquí se eligen los adaptadores según el perfil."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.monitoring.adapters.inbound.events import register_monitoring
from spaceapp.modules.monitoring.adapters.inbound.rest import build_router as monitoring_router
from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.adapters.outbound.telemetry_readings import TelemetryReadings
from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.modules.monitoring.domain.rules import RuleCatalog
from spaceapp.modules.telemetry.adapters.inbound.events import register_telemetry
from spaceapp.modules.telemetry.adapters.inbound.rest import build_router as telemetry_router
from spaceapp.modules.telemetry.adapters.outbound.layout_json import load_layout
from spaceapp.modules.telemetry.adapters.outbound.sql import SqlTelemetryRepository
from spaceapp.modules.telemetry.application.rollup import RecomputeRollup
from spaceapp.modules.telemetry.application.simulation import SimulationService
from spaceapp.platform.bus import SubscriptionRegistry
from spaceapp.platform.config import Settings
from spaceapp.platform.db import make_engine, make_session_factory
from spaceapp.platform.outbox import OutboxRelay, outbox_stats


def _with_session[T](factory: Callable[[AsyncSession], T]) -> Callable[[AsyncSession | None], T]:
    """Los adaptadores SQL necesitan la sesión del handler; en memoria no aplican."""

    def build(session: AsyncSession | None) -> T:
        if session is None:
            raise RuntimeError("este adaptador necesita la sesión del relay del outbox")
        return factory(session)

    return build


def build_registry(settings: Settings, catalog: RuleCatalog) -> SubscriptionRegistry:
    registry = SubscriptionRegistry()
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
                build_registry(settings, app.state.catalog),
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
    app.state.sim = None
    app.state.relay_task = app.state.simulator_task = None
    app.include_router(monitoring_router(app.state.catalog))
    app.include_router(telemetry_router(get_simulation))

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
