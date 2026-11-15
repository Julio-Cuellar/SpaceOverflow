"""Cruza el catálogo de reglas de Monitoreo (dev A) con el de Conocimiento.

Una alerta de una regla que Conocimiento no conoce se queda sin recomendación, y el evento
termina en el outbox como fallido. Estas pruebas lo detectan al cambiar cualquiera de los dos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource

ROOT = Path(__file__).resolve().parents[2]
MONITORING_RULES = json.loads(
    (ROOT / "rules" / "catalog" / "monitoring.json").read_text(encoding="utf-8")
)["rules"]
BY_KEY: dict[str, dict[str, Any]] = {rule["key"]: rule for rule in MONITORING_RULES}

# De menos a más respaldo. Una recomendación nunca puede decir más que la regla que la originó.
STRENGTH = {"DEMO": 0, "NO_VERIFICADO": 1, "TB": 2, "VERIFICADO": 3}
REQUIREMENT = re.compile(r"^(V[12] \d{4})\b")


@pytest.mark.parametrize("rule_key", list(BY_KEY))
def test_every_rule_that_monitoring_can_raise_has_a_recommendation(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    assert rule_key in demo_source.rule_keys()


def test_the_knowledge_catalog_has_no_rule_that_monitoring_never_raises(
    demo_source: DemoKnowledgeSource,
) -> None:
    assert set(demo_source.rule_keys()) - set(BY_KEY) == set()


@pytest.mark.parametrize("rule_key", list(BY_KEY))
def test_the_action_that_monitoring_names_is_among_the_recommended_ones(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    keys = [a.key for a in demo_source.guidance_for(rule_key).actions]

    assert BY_KEY[rule_key]["action_key"] in keys
    assert demo_source.action(BY_KEY[rule_key]["action_key"]) is not None


@pytest.mark.parametrize("rule_key", list(BY_KEY))
def test_a_citation_never_claims_more_evidence_than_the_rule_it_comes_from(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    allowed = STRENGTH[BY_KEY[rule_key]["evidence_state"]]

    for citation in demo_source.guidance_for(rule_key).citations:
        assert STRENGTH[citation.evidence_state.value] <= allowed, (rule_key, citation)


@pytest.mark.parametrize("rule_key", list(BY_KEY))
def test_a_requirement_named_by_monitoring_is_the_one_cited(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    match = REQUIREMENT.match(BY_KEY[rule_key]["source_requirement"])
    if match is None:
        pytest.skip("la regla no cita un número de requisito")

    cited = {c.requirement_ref for c in demo_source.guidance_for(rule_key).citations}

    assert match.group(1) in cited


@pytest.mark.parametrize("rule_key", list(BY_KEY))
def test_every_recommendation_of_a_rule_with_demo_evidence_is_not_presented_as_verified(
    demo_source: DemoKnowledgeSource, rule_key: str
) -> None:
    if BY_KEY[rule_key]["evidence_state"] != "DEMO":
        pytest.skip("la regla tiene respaldo")

    states = {c.evidence_state.value for c in demo_source.guidance_for(rule_key).citations}

    assert states == {"DEMO"}
