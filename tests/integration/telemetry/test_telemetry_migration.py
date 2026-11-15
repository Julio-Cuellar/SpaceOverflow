import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def cols(url: str, table: str) -> set[str]:
    return {c["name"] for c in inspect(create_engine(url)).get_columns(table, schema="telemetry")}


def test_the_telemetry_tables_have_the_agreed_columns(pg_sync_url: str):
    assert cols(pg_sync_url, "sensor") == {
        "id",
        "habitat_id",
        "zone_id",
        "crew_member_id",
        "domain",
        "metric",
        "unit",
        "sample_period_s",
        "origin",
    }
    assert cols(pg_sync_url, "reading") == {"sensor_id", "ts", "value", "quality"}
    assert cols(pg_sync_url, "reading_rollup_1m") == {
        "sensor_id",
        "bucket",
        "avg_v",
        "min_v",
        "max_v",
        "n",
    }
    assert cols(pg_sync_url, "scenario_run") == {
        "id",
        "habitat_id",
        "zone_id",
        "scenario_key",
        "state",
        "speed",
        "started_at",
        "stopped_at",
    }


def test_readings_are_partitioned_by_range_on_the_timestamp(pg_sync_url: str):
    with create_engine(pg_sync_url).connect() as c:
        strat = c.execute(
            text(
                "SELECT partstrat FROM pg_partitioned_table WHERE partrelid = 'telemetry.reading'::regclass"
            )
        ).scalar_one()
        pk = inspect(c).get_pk_constraint("reading", schema="telemetry")["constrained_columns"]
    assert strat == "r" and pk == ["sensor_id", "ts"]


def test_there_is_a_brin_index_on_the_timestamp(pg_sync_url: str):
    with create_engine(pg_sync_url).connect() as c:
        defs = (
            c.execute(
                text(
                    "SELECT indexdef FROM pg_indexes WHERE schemaname='telemetry' AND tablename='reading' "
                    "AND indexdef ILIKE '%brin%'"
                )
            )
            .scalars()
            .all()
        )
    assert defs and "ts" in defs[0]


def test_ensure_partition_creates_a_daily_partition_and_can_run_twice(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    for _ in range(2):
        with eng.begin() as c:
            c.execute(text("SELECT telemetry.ensure_reading_partition(DATE '2030-01-15')"))
    with eng.connect() as c:
        bound = c.execute(
            text(
                "SELECT pg_get_expr(c.relpartbound, c.oid) FROM pg_class c "
                "WHERE c.relname = 'reading_20300115' AND c.relnamespace = 'telemetry'::regnamespace"
            )
        ).scalar_one()
    assert "2030-01-15" in bound and "2030-01-16" in bound


def test_domain_and_origin_only_accept_the_known_values(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    with pytest.raises(IntegrityError), eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO telemetry.sensor (id, habitat_id, domain, metric, unit, sample_period_s, "
                "origin) VALUES (gen_random_uuid(), gen_random_uuid(), 'cabin', 'x', 'u', 1, 'MAGIC')"
            )
        )
    with pytest.raises(IntegrityError), eng.begin() as c:
        c.execute(
            text(
                "INSERT INTO telemetry.sensor (id, habitat_id, domain, metric, unit, sample_period_s, "
                "origin) VALUES (gen_random_uuid(), gen_random_uuid(), 'other', 'x', 'u', 1, 'SIMULATED')"
            )
        )
