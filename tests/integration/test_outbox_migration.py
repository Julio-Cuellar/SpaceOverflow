import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config

pytestmark = pytest.mark.integration


def test_outbox_event_has_the_agreed_columns(pg_sync_url: str):
    cols = {
        c["name"]
        for c in inspect(create_engine(pg_sync_url)).get_columns("outbox_event", schema="platform")
    }
    assert cols == {
        "id",
        "event_id",
        "type",
        "version",
        "aggregate_type",
        "aggregate_id",
        "partition_key",
        "correlation_id",
        "causation_id",
        "payload",
        "occurred_at",
        "status",
        "attempts",
        "next_attempt_at",
        "last_error",
    }


def test_inbox_primary_key_is_consumer_and_event(pg_sync_url: str):
    pk = inspect(create_engine(pg_sync_url)).get_pk_constraint("inbox_processed", schema="platform")
    assert pk["constrained_columns"] == ["consumer", "event_id"]


def test_there_is_a_partial_index_for_pending_events(pg_sync_url: str):
    with create_engine(pg_sync_url).connect() as c:
        defs = (
            c.execute(
                text(
                    "SELECT indexdef FROM pg_indexes WHERE schemaname='platform' "
                    "AND indexname='outbox_pending_idx'"
                )
            )
            .scalars()
            .all()
        )
    assert len(defs) == 1
    assert "WHERE" in defs[0] and "pending" in defs[0]


def _insert(c, event_id: str, status: str = "pending") -> None:  # type: ignore[no-untyped-def]
    c.execute(
        text(
            "INSERT INTO platform.outbox_event (event_id, type, aggregate_type, aggregate_id, "
            "partition_key, payload, status) VALUES (:e, 'demo.pinged', 'demo', "
            "gen_random_uuid(), 'k', '{}', :s)"
        ),
        {"e": event_id, "s": status},
    )


def test_status_only_accepts_the_known_values(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    with pytest.raises(IntegrityError), eng.begin() as c:
        _insert(c, "00000000-0000-4000-8000-0000000000a1", status="raro")


def test_event_id_is_unique(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    eid = "00000000-0000-4000-8000-0000000000b1"
    with eng.begin() as c:
        c.execute(text("TRUNCATE platform.outbox_event"))
        _insert(c, eid)
    with pytest.raises(IntegrityError), eng.begin() as c:
        _insert(c, eid)
    with eng.begin() as c:
        c.execute(text("TRUNCATE platform.outbox_event"))


def test_migration_can_be_downgraded_and_upgraded_again(pg_sync_url: str):
    cfg = alembic_config("platform", pg_sync_url)
    command.downgrade(cfg, "base")
    assert not inspect(create_engine(pg_sync_url)).has_table("outbox_event", schema="platform")
    command.upgrade(cfg, "head")
    assert inspect(create_engine(pg_sync_url)).has_table("outbox_event", schema="platform")


def test_the_migration_command_applies_pending_migrations(
    pg_sync_url: str,
    async_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    from spaceapp.platform import migrate

    cfg = alembic_config("platform", pg_sync_url)
    command.downgrade(cfg, "base")
    monkeypatch.setenv("SPACEAPP_DATABASE_URL", async_url)
    monkeypatch.setattr("sys.argv", ["migrate", "platform"])
    migrate.main()
    assert "applied" in capsys.readouterr().out
    assert inspect(create_engine(pg_sync_url)).has_table("outbox_event", schema="platform")
