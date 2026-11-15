import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def cols(url: str, table: str) -> set[str]:
    return {c["name"] for c in inspect(create_engine(url)).get_columns(table, schema="monitoring")}


def test_the_rule_table_stores_the_whole_catalog_entry(pg_sync_url: str):
    assert cols(pg_sync_url, "rule") == {
        "id",
        "key",
        "version",
        "kind",
        "parameter",
        "operator",
        "threshold",
        "unit",
        "window_s",
        "severity",
        "source_requirement",
        "source_document",
        "evidence_state",
        "hrp_hazard",
        "action_key",
        "active",
        "params",
        "supersedes",
    }


def test_the_alert_table_has_lifecycle_and_audit_columns(pg_sync_url: str):
    assert cols(pg_sync_url, "alert") == {
        "id",
        "rule_id",
        "habitat_id",
        "zone_id",
        "crew_member_id",
        "severity",
        "status",
        "cause_hint",
        "evidence",
        "dedupe_key",
        "clear_streak",
        "raised_at",
        "acknowledged_at",
        "resolved_at",
    }
    assert cols(pg_sync_url, "alert_ack") == {"id", "alert_id", "crew_member_id", "note", "at"}


def _rule(c) -> str:  # type: ignore[no-untyped-def]
    return c.execute(
        text(
            "INSERT INTO monitoring.rule (id, key, kind, parameter, operator, threshold, unit, "
            "window_s, severity, source_requirement, source_document, evidence_state, hrp_hazard, "
            "action_key) VALUES (gen_random_uuid(), :k, 'umbral', 'ppco2', '>', 3, 'mmHg', 0, "
            "'alerta', 'V2 6004', 'doc', 'VERIFICADO', 'h', 'a') RETURNING id"
        ),
        {"k": "k-" + __import__("uuid").uuid4().hex},
    ).scalar_one()


def _alert(c, rule_id, dedupe: str, status: str = "raised") -> None:  # type: ignore[no-untyped-def]
    c.execute(
        text(
            "INSERT INTO monitoring.alert (id, rule_id, habitat_id, severity, status, evidence, "
            "dedupe_key, raised_at) VALUES "
            "(gen_random_uuid(), :r, gen_random_uuid(), 'alerta', :s, "
            "'{}', :d, now())"
        ),
        {"r": rule_id, "s": status, "d": dedupe},
    )


def test_only_one_active_alert_can_exist_per_rule_and_zone(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    with eng.begin() as c:
        rid = _rule(c)
        _alert(c, rid, "env-co2-1h:zona-1")
    with pytest.raises(IntegrityError), eng.begin() as c:
        _alert(c, rid, "env-co2-1h:zona-1")
    with eng.begin() as c:
        c.execute(text("TRUNCATE monitoring.alert, monitoring.rule CASCADE"))


def test_a_resolved_alert_does_not_block_a_new_one_with_the_same_key(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    with eng.begin() as c:
        rid = _rule(c)
        _alert(c, rid, "env-co2-1h:zona-2", status="resolved")
        _alert(c, rid, "env-co2-1h:zona-2", status="raised")
        c.execute(text("TRUNCATE monitoring.alert, monitoring.rule CASCADE"))


def test_the_status_only_accepts_the_known_values(pg_sync_url: str):
    eng = create_engine(pg_sync_url)
    with pytest.raises(IntegrityError), eng.begin() as c:
        _alert(c, _rule(c), "x", status="rara")
