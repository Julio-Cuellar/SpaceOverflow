from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.domain.engine import RuleHit
from spaceapp.modules.monitoring.domain.rules import Rule, RuleCatalog

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
H, Z = uuid4(), uuid4()
T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def hit(key: str = "env-co2-1h") -> RuleHit:
    r = CATALOG.by_key()[key]
    return RuleHit(
        rule_key=key,
        zone_id=Z,
        parameter=r.parameter,
        severity=r.severity,
        value=3.4,
        unit=r.unit,
        operator=r.operator,
        threshold=r.threshold,
        window_s=r.window_s,
        band="x",
        kind=r.kind,
        evidence_state=r.evidence_state,
        source_requirement=r.source_requirement,
        source_document=r.source_document,
        hrp_hazard=r.hrp_hazard,
        action_key=r.action_key,
    )


async def rows(sf, sql: str):  # type: ignore[no-untyped-def]
    async with sf() as s:
        return [dict(r) for r in (await s.execute(text(sql))).mappings().all()]


async def test_ensure_rules_stores_the_catalog_and_is_idempotent(session_factory):
    for _ in range(2):
        async with session_factory() as s, s.begin():
            await SqlAlertRepository(s).ensure_rules(CATALOG)
    got = await rows(session_factory, "SELECT key, version FROM monitoring.rule")
    assert len(got) == len(CATALOG.rules) and {r["version"] for r in got} == {1}


async def test_a_changed_rule_is_updated_and_its_version_goes_up(session_factory):
    async with session_factory() as s, s.begin():
        await SqlAlertRepository(s).ensure_rules(CATALOG)
    changed = tuple(
        Rule(**{**r.__dict__, "threshold": 3.5}) if r.key == "env-co2-1h" else r
        for r in CATALOG.rules
    )
    async with session_factory() as s, s.begin():
        await SqlAlertRepository(s).ensure_rules(RuleCatalog("v2", changed))
    got = {
        r["key"]: r
        for r in await rows(session_factory, "SELECT key, version, threshold FROM monitoring.rule")
    }
    assert (float(got["env-co2-1h"]["threshold"]), got["env-co2-1h"]["version"]) == (3.5, 2)
    assert got["env-n2"]["version"] == 1


async def test_add_persists_the_alert_with_evidence_and_dedupe_key(session_factory):
    async with session_factory() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        alert_id = await repo.add(H, Z, hit(), T0)
    (row,) = await rows(session_factory, "SELECT * FROM monitoring.alert")
    assert row["id"] == alert_id and row["status"] == "raised" and row["severity"] == "alert"
    assert row["dedupe_key"] == f"env-co2-1h:{Z}" and row["evidence"]["value"] == 3.4
    assert row["cause_hint"] == "ENVIRONMENT" and row["raised_at"] == T0


async def test_the_database_refuses_a_second_active_alert_for_the_same_rule_and_zone(
    session_factory,
):
    async with session_factory() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        await repo.add(H, Z, hit(), T0)
    with pytest.raises(IntegrityError):
        async with session_factory() as s, s.begin():
            await SqlAlertRepository(s).add(H, Z, hit(), T0)


async def test_active_for_zone_returns_only_unresolved_alerts_of_that_zone(session_factory):
    async with session_factory() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        a = await repo.add(H, Z, hit("env-co2-1h"), T0)
        b = await repo.add(H, Z, hit("env-rh-high"), T0)
        await repo.resolve(b, T0 + timedelta(seconds=30))
    async with session_factory() as s:
        active = await SqlAlertRepository(s).active_for_zone(H, Z)
        other = await SqlAlertRepository(s).active_for_zone(H, uuid4())
    assert [x.id for x in active] == [a] and active[0].rule_key == "env-co2-1h" and other == []


async def test_touch_set_streak_and_resolve_update_the_alert(session_factory):
    async with session_factory() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        alert_id = await repo.add(H, Z, hit(), T0)
        await repo.set_streak(alert_id, 2)
        await repo.touch(alert_id, {"value": 9.9})
        assert (await repo.active_for_zone(H, Z))[0].clear_streak == 0
        await repo.set_streak(alert_id, 2)
        duration = await repo.resolve(alert_id, T0 + timedelta(seconds=45))
    assert duration == 45
    (row,) = await rows(
        session_factory, "SELECT status, resolved_at, clear_streak, evidence FROM monitoring.alert"
    )
    assert row["status"] == "resolved" and row["evidence"]["value"] == 9.9


async def test_a_resolved_alert_allows_a_new_one_for_the_same_rule_and_zone(session_factory):
    async with session_factory() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        first = await repo.add(H, Z, hit(), T0)
        await repo.resolve(first, T0 + timedelta(seconds=10))
        second = await repo.add(H, Z, hit(), T0 + timedelta(seconds=20))
    assert first != second
