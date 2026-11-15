"""Migration 0002 numbers the tickets that already existed, without losing any."""

from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import create_engine, text

from tests.conftest import alembic_config

pytestmark = pytest.mark.integration


def test_existing_tickets_get_distinct_numbers_when_the_column_is_added(pg_sync_url: str) -> None:
    cfg = alembic_config("facility", pg_sync_url)
    engine = create_engine(pg_sync_url)
    command.downgrade(cfg, "0001")
    try:
        with engine.begin() as c:
            c.execute(
                text(
                    "TRUNCATE facility.incident_update, facility.incident, facility.zone, facility.habitat CASCADE"
                )
            )
            c.execute(
                text(
                    "INSERT INTO facility.habitat VALUES (gen_random_uuid(), 'h', 'H', 'ship', 101.3)"
                )
            )
            c.execute(
                text(
                    "INSERT INTO facility.zone (id, habitat_id, code, name, kind, deck, layout) "
                    "SELECT gen_random_uuid(), id, 'z', 'Z', 'k', 1, '{}' FROM facility.habitat"
                )
            )
            for n in range(3):
                c.execute(
                    text(
                        "INSERT INTO facility.incident (id, habitat_id, zone_id, type_key, source, "
                        "title, description, severity, opened_at) SELECT gen_random_uuid(), z.habitat_id, "
                        "z.id, 't', 'MANUAL', :t, 'd', 'alert', now() FROM facility.zone z"
                    ),
                    {"t": f"old {n}"},
                )
        command.upgrade(cfg, "head")
        with engine.connect() as c:
            numbers = [
                r[0]
                for r in c.execute(text("SELECT number FROM facility.incident ORDER BY number"))
            ]
        assert len(numbers) == 3 and len(set(numbers)) == 3 and None not in numbers
    finally:
        command.upgrade(cfg, "head")
        with engine.begin() as c:
            c.execute(
                text(
                    "TRUNCATE facility.incident_update, facility.incident, facility.zone, facility.habitat CASCADE"
                )
            )
        engine.dispose()
