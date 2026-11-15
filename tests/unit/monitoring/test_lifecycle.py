from uuid import uuid4

from spaceapp.modules.monitoring.domain.engine import RuleHit
from spaceapp.modules.monitoring.domain.lifecycle import ActiveAlert, ack_decision, reconcile

Z = uuid4()


def hit(key: str = "env-co2-1h", zone=Z, severity: str = "alert") -> RuleHit:
    return RuleHit(
        rule_key=key,
        zone_id=zone,
        parameter="ppco2",
        severity=severity,
        value=3.4,
        unit="mmHg",
        operator=">",
        threshold=3.0,
        window_s=3600,
        band="above 3 mmHg",
        kind="threshold",
        evidence_state="VERIFIED",
        source_requirement="V2 6004",
        source_document="NASA-STD-3001 Vol. 2 Rev F",
        hrp_hazard="hostile_closed_environments",
        action_key="check_ventilation_and_filters",
    )


def active(key: str = "env-co2-1h", zone=Z, streak: int = 0, status: str = "raised") -> ActiveAlert:
    return ActiveAlert(
        id=uuid4(),
        rule_key=key,
        zone_id=zone,
        severity="alert",
        status=status,
        clear_streak=streak,
    )


def test_a_new_hit_raises_an_alert():
    d = reconcile([], [hit()], superseded=frozenset(), hysteresis=3)
    assert [h.rule_key for h in d.raise_hits] == ["env-co2-1h"]
    assert d.keep == d.clearing == d.resolve == []


def test_a_hit_on_an_active_alert_keeps_it_without_raising_again():
    a = active(streak=2)
    d = reconcile([a], [hit()], superseded=frozenset(), hysteresis=3)
    assert d.raise_hits == [] and d.keep[0][0] is a and d.resolve == [] and d.clearing == []


def test_an_alert_is_resolved_only_after_enough_clean_evaluations():
    a = active()
    d1 = reconcile([a], [], superseded=frozenset(), hysteresis=3)
    assert d1.clearing == [(a, 1)] and d1.resolve == []
    a2 = ActiveAlert(**{**a.__dict__, "clear_streak": 2})
    d3 = reconcile([a2], [], superseded=frozenset(), hysteresis=3)
    assert d3.resolve == [a2] and d3.clearing == []


def test_a_hit_during_the_clearing_phase_restarts_the_count():
    a = active(streak=2)
    d = reconcile([a], [hit()], superseded=frozenset(), hysteresis=3)
    assert d.keep and d.resolve == []


def test_a_superseded_alert_is_resolved_at_once_even_without_hysteresis():
    mild = active(key="env-pio2-low-pre")
    d = reconcile(
        [mild], [hit(key="env-pio2-low")], superseded=frozenset({"env-pio2-low-pre"}), hysteresis=3
    )
    assert d.resolve == [mild]
    assert [h.rule_key for h in d.raise_hits] == ["env-pio2-low"]


def test_zones_do_not_interfere():
    other = uuid4()
    a = active(zone=other)
    d = reconcile([a], [hit(zone=Z)], superseded=frozenset(), hysteresis=3)
    assert [h.zone_id for h in d.raise_hits] == [Z]
    assert d.clearing == [(a, 1)]


def test_an_acknowledged_alert_is_still_active_and_follows_the_same_rules():
    a = active(status="acknowledged", streak=2)
    d = reconcile([a], [], superseded=frozenset(), hysteresis=3)
    assert d.resolve == [a]


def test_acknowledging_is_idempotent_and_not_allowed_after_resolution():
    assert ack_decision("raised") == "acknowledge"
    assert ack_decision("acknowledged") == "already"
    assert ack_decision("resolved") == "resolved"
