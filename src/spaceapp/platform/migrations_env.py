"""Shared Alembic environment: one schema and one version table per module."""

from alembic import context
from sqlalchemy import create_engine, pool, text


def run(schema: str) -> None:
    url = context.config.get_main_option("sqlalchemy.url")
    assert url, (
        "sqlalchemy.url is missing (use the psycopg driver, for example postgresql+psycopg://...)"
    )
    if context.is_offline_mode():
        raise RuntimeError("Migrations are applied online")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table=f"alembic_version_{schema}",
            version_table_schema=schema,
        )
        with context.begin_transaction():
            context.run_migrations()
