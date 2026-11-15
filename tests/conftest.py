"""Fixtures comunes. Las de integración levantan PostgreSQL real con testcontainers."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SOCK = Path.home() / ".docker" / "desktop" / "docker.sock"
MIGRATED_MODULES = ["platform", "monitoring", "telemetry"]
CLEAN_TABLES = [
    "platform.outbox_event",
    "platform.inbox_processed",
    "monitoring.alert_ack",
    "monitoring.alert",
    "monitoring.rule",
    "telemetry.reading_rollup_1m",
    "telemetry.reading",
    "telemetry.scenario_run",
    "telemetry.sensor",
]


def _point_docker_to_desktop_socket() -> None:
    no_default_socket = not Path("/var/run/docker.sock").exists()
    if "DOCKER_HOST" not in os.environ and no_default_socket and DESKTOP_SOCK.exists():
        os.environ["DOCKER_HOST"] = f"unix://{DESKTOP_SOCK}"
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


def alembic_config(module: str, url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "migrations" / module))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def pg_sync_url() -> Iterator[str]:
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:  # versiones anteriores de testcontainers
        from testcontainers.postgres import PostgresContainer

    _point_docker_to_desktop_socket()
    with PostgresContainer(
        "pgvector/pgvector:pg16",
        username="spaceapp",
        password="spaceapp",
        dbname="spaceapp",
        driver="psycopg",
    ) as pg:
        url = pg.get_connection_url()
        for module in MIGRATED_MODULES:
            command.upgrade(alembic_config(module, url), "head")
        yield url


@pytest.fixture
def async_url(pg_sync_url: str) -> str:
    return pg_sync_url.replace("+psycopg", "+asyncpg")


@pytest.fixture
def listen_dsn(pg_sync_url: str) -> str:
    return pg_sync_url.replace("+psycopg", "")


@pytest.fixture
async def engine(async_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(async_url)
    async with eng.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(CLEAN_TABLES)} RESTART IDENTITY CASCADE"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS public.demo_state (v text)"))
        await conn.execute(text("TRUNCATE public.demo_state"))
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine):  # type: ignore[no-untyped-def]
    return async_sessionmaker(engine, expire_on_commit=False)
