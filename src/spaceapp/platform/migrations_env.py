"""Entorno de Alembic compartido: un esquema y una tabla de versión por módulo."""

from alembic import context
from sqlalchemy import create_engine, pool, text


def run(schema: str) -> None:
    url = context.config.get_main_option("sqlalchemy.url")
    assert url, "falta sqlalchemy.url (use el driver psycopg, por ejemplo postgresql+psycopg://...)"
    if context.is_offline_mode():
        raise RuntimeError("Las migraciones se aplican en línea")
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
