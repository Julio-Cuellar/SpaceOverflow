from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.adapters.outbound.sql import SqlAlertRepository
from spaceapp.modules.monitoring.application.acknowledge_alert import (
    Acknowledged,
    AlertAlreadyResolved,
    AlertNotFound,
    AlreadyAcknowledged,
    acknowledge_alert,
)
from spaceapp.modules.monitoring.contracts import AlertAcknowledged
from spaceapp.modules.monitoring.domain.engine import RuleHit

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_catalog(ROOT / "rules" / "catalog" / "monitoring.json")
H, Z, CREW = uuid4(), uuid4(), uuid4()
T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


async def new_alert(sf):  # type: ignore[no-untyped-def]
    r = CATALOG.by_key()["env-co2-1h"]
    h = RuleHit(
        r.key,
        Z,
        r.parameter,
        r.severity,
        3.4,
        r.unit,
        r.operator,
        r.threshold,
        r.window_s,
        "x",
        r.kind,
        r.evidence_state,
        r.source_requirement,
        r.source_document,
        r.hrp_hazard,
        r.action_key,
    )
    async with sf() as s, s.begin():
        repo = SqlAlertRepository(s)
        await repo.ensure_rules(CATALOG)
        return await repo.add(H, Z, h, T0)


async def ack(sf, alert_id, **kw):  # type: ignore[no-untyped-def]
    return await acknowledge_alert(
        sf, SqlAlertRepository, alert_id, CREW, now=T0 + timedelta(seconds=5), **kw
    )


async def count(sf, table: str) -> int:  # type: ignore[no-untyped-def]
    async with sf() as s:
        return (await s.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def test_acknowledging_marks_the_alert_and_publishes_one_event(session_factory):
    alert_id = await new_alert(session_factory)
    result = await ack(session_factory, alert_id, note="checking filters")
    assert result == Acknowledged(alert_id)
    async with session_factory() as s:
        row = (await s.execute(text("SELECT status, acknowledged_at FROM monitoring.alert"))).one()
        ev = (
            await s.execute(
                text("SELECT payload, aggregate_id, partition_key FROM platform.outbox_event")
            )
        ).one()
        note = (
            await s.execute(text("SELECT note, crew_member_id FROM monitoring.alert_ack"))
        ).one()
    assert row.status == "acknowledged" and row.acknowledged_at == T0 + timedelta(seconds=5)
    payload = AlertAcknowledged.model_validate(ev.payload)
    assert (payload.alert_id, payload.crew_member_id) == (alert_id, CREW)
    assert ev.aggregate_id == alert_id and ev.partition_key == f"habitat:{H}"
    assert (note.note, note.crew_member_id) == ("checking filters", CREW)


async def test_acknowledging_twice_is_idempotent_and_publishes_nothing_more(session_factory):
    alert_id = await new_alert(session_factory)
    await ack(session_factory, alert_id)
    assert await ack(session_factory, alert_id) == AlreadyAcknowledged(alert_id)
    assert await count(session_factory, "platform.outbox_event") == 1
    assert await count(session_factory, "monitoring.alert_ack") == 1


async def test_an_unknown_alert_is_reported_without_side_effects(session_factory):
    assert await ack(session_factory, uuid4()) == AlertNotFound()
    assert await count(session_factory, "platform.outbox_event") == 0


async def test_a_resolved_alert_cannot_be_acknowledged(session_factory):
    alert_id = await new_alert(session_factory)
    async with session_factory() as s, s.begin():
        await SqlAlertRepository(s).resolve(alert_id, T0 + timedelta(seconds=1))
    assert await ack(session_factory, alert_id) == AlertAlreadyResolved(alert_id)
    assert await count(session_factory, "platform.outbox_event") == 0
