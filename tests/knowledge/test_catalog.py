from __future__ import annotations

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.domain.model import EvidenceState


def test_every_rule_has_at_least_two_actions(demo_source: DemoKnowledgeSource) -> None:
    for rule_key in demo_source.rule_keys():
        assert len(demo_source.guidance_for(rule_key).actions) >= 2, rule_key


def test_every_action_key_exists_in_the_action_catalog(demo_source: DemoKnowledgeSource) -> None:
    for rule_key in demo_source.rule_keys():
        for action in demo_source.guidance_for(rule_key).actions:
            assert demo_source.action_title(action.key) is not None, action.key


def test_every_rule_is_labelled_as_demo_source(demo_source: DemoKnowledgeSource) -> None:
    for rule_key in demo_source.rule_keys():
        assert demo_source.guidance_for(rule_key).source_kind == "DEMO", rule_key


def test_every_citation_uses_a_known_evidence_state(demo_source: DemoKnowledgeSource) -> None:
    allowed = {state.value for state in EvidenceState}
    for rule_key in demo_source.rule_keys():
        for citation in demo_source.guidance_for(rule_key).citations:
            assert citation.evidence_state.value in allowed, rule_key


def test_the_catalog_covers_the_rules_of_the_plan(demo_source: DemoKnowledgeSource) -> None:
    expected = {
        "env-co2-1h",
        "env-pio2",
        "env-ptotal",
        "env-dpdt",
        "env-n2",
        "env-rh",
        "env-t",
        "env-tendencia",
    }

    assert expected <= set(demo_source.rule_keys())
