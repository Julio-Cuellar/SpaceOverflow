import json
from pathlib import Path

import pytest

from spaceapp.modules.monitoring.adapters.outbound.catalog_json import load_catalog
from spaceapp.modules.monitoring.domain.rules import InvalidRule, Rule, RuleCatalog

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "rules" / "catalog" / "monitoring.json"


def rule(**over) -> Rule:
    base = dict(
        key="x-1",
        kind="threshold",
        parameter="ppco2",
        operator=">",
        threshold=3.0,
        unit="mmHg",
        window_s=0,
        severity="alert",
        source_requirement="V2 6004",
        source_document="NASA-STD-3001 Vol. 2 Rev F",
        evidence_state="VERIFIED",
        hrp_hazard="hostile_closed_environments",
        action_key="check_ventilation_and_filters",
    )
    return Rule(**{**base, **over})


def test_a_valid_rule_is_created():
    assert rule().active is True


@pytest.mark.parametrize(
    "bad",
    [
        {"source_requirement": ""},
        {"source_document": " "},
        {"evidence_state": "INVENTED"},
        {"severity": "rojo"},
        {"operator": "=="},
        {"kind": "magia"},
        {"window_s": -1},
        {"key": ""},
    ],
)
def test_a_rule_without_source_or_with_bad_fields_is_rejected(bad):
    with pytest.raises(InvalidRule):
        rule(**bad)


def test_a_trend_rule_can_only_be_a_demo_rule():
    with pytest.raises(InvalidRule, match="DEMO"):
        rule(kind="trend", evidence_state="VERIFIED")
    assert rule(kind="trend", evidence_state="DEMO").kind == "trend"


def test_catalog_rejects_duplicate_keys_and_unknown_supersedes():
    with pytest.raises(InvalidRule, match="duplicate"):
        RuleCatalog(version="v", rules=(rule(), rule()))
    with pytest.raises(InvalidRule, match="supersedes"):
        RuleCatalog(version="v", rules=(rule(supersedes=("no-existe",)),))


def test_the_real_catalog_loads_and_every_rule_has_a_source_and_evidence_state():
    cat = load_catalog(CATALOG)
    assert len(cat.rules) >= 20
    for r in cat.rules:
        assert r.source_requirement and r.source_document
        assert r.evidence_state in {"VERIFIED", "TB", "DEMO"}


def test_the_catalog_version_changes_when_the_content_changes(tmp_path):
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    a = tmp_path / "a.json"
    a.write_text(json.dumps(data), encoding="utf-8")
    data["rules"][0]["threshold"] = data["rules"][0]["threshold"] + 1
    b = tmp_path / "b.json"
    b.write_text(json.dumps(data), encoding="utf-8")
    assert load_catalog(a).version != load_catalog(b).version


def test_verified_limits_of_the_norm_are_in_the_catalog_with_the_right_numbers():
    cat = load_catalog(CATALOG)
    by = {r.key: r for r in cat.rules}
    assert (by["env-co2-1h"].threshold, by["env-co2-1h"].window_s) == (3.0, 3600)
    assert by["env-co2-1h"].evidence_state == "VERIFIED"
    assert by["env-pio2-low"].threshold == 127 and by["env-pio2-low"].evidence_state == "VERIFIED"
    assert by["env-pio2-abs-low"].threshold == 122
    assert by["env-pio2-high"].threshold == 356
    assert by["env-ptotal-low"].threshold == 34.5 and by["env-ptotal-high"].threshold == 103
    assert by["env-dpdt"].threshold == 13.5 and by["env-dpdt"].params["min_change_psi"] == 1.0
    assert by["env-dpdt"].window_s == 10  # short window: a real leak is not averaged over 60 s
    assert by["env-n2"].threshold == 30


def test_the_proposed_bands_are_marked_as_demo():
    by = {r.key: r for r in load_catalog(CATALOG).rules}
    for key in (
        "env-pio2-low-pre",
        "env-pio2-high-pre",
        "env-co2-pre",
        "env-rh-low-pre",
        "env-t-high",
    ):
        assert by[key].evidence_state == "DEMO", key


def test_every_supersedes_reference_exists_in_the_real_catalog():
    cat = load_catalog(CATALOG)
    keys = {r.key for r in cat.rules}
    for r in cat.rules:
        assert set(r.supersedes) <= keys
