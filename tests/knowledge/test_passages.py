from __future__ import annotations

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.domain.model import EvidenceState


def test_finds_the_tb004_headache_passage_for_a_headache_question(
    demo_source: DemoKnowledgeSource,
) -> None:
    passages = demo_source.search("Why do I have a headache?", k=3)

    assert passages[0].document_code == "OCHMO-TB-004 CO₂"
    assert passages[0].evidence_state is EvidenceState.TB


def test_returns_nothing_when_no_passage_is_relevant(demo_source: DemoKnowledgeSource) -> None:
    assert demo_source.search("How do I change the airlock filter?", k=3) == []


def test_returns_at_most_k_passages(demo_source: DemoKnowledgeSource) -> None:
    assert len(demo_source.search("headache fatigue hypoxia", k=1)) == 1


def test_ignores_case_and_accents(demo_source: DemoKnowledgeSource) -> None:
    assert demo_source.search("HEADACHE", k=3)
    assert demo_source.search("headache", k=3)
