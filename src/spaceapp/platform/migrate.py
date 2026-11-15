"""Aplica las migraciones de un módulo: `python -m spaceapp.platform.migrate <modulo>`."""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from spaceapp.platform.config import Settings

ROOT = Path(__file__).resolve().parents[3]


def upgrade(module: str, sync_url: str) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "migrations" / module))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


def main() -> None:
    module = sys.argv[1] if len(sys.argv) > 1 else "platform"
    url = Settings().database_url.replace("+asyncpg", "+psycopg")
    upgrade(module, url)
    print(f"migraciones de {module!r} aplicadas")


if __name__ == "__main__":
    main()
