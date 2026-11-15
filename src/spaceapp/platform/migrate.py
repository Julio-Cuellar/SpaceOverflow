"""Applies a module's migrations: `python -m spaceapp.platform.migrate <module>`."""

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
    print(f"migrations of {module!r} applied")


if __name__ == "__main__":
    main()
