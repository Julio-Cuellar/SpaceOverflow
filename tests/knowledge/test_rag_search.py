from __future__ import annotations

import json
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.rag_source import (
    FallbackKnowledgeSource,
    RagKnowledgeSource,
)
from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.ingest.chunking import Chunk, chunk_page
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY = ROOT / "data" / "knowledge" / "glossary_es_en.json"
STANDARD = "NASA-STD-3001 Vol. 2 Rev F"
BRIEF = "OCHMO-TB-004 CO₂"
MEDICAL = "OCHMO-TB-044 operaciones médicas"


def corpus() -> list[Chunk]:
    return [
        *chunk_page(
            STANDARD,
            5,
            "[V2 6004] The ppCO2 average over 1 hour shall be less than or equal to 3 mmHg.",
            "VERIFICADO",
        ),
        *chunk_page(
            BRIEF,
            2,
            "Headache can occur between 2.8 and 4.5 mmHg of ppCO2. "
            "Fatigue, poor sleep and nausea appear above 4.5 mmHg.",
            "TB",
        ),
        *chunk_page(
            STANDARD,
            4,
            "[V2 6003] Normoxia is a PIO2 between 145 and 155 mmHg. Hypoxia occurs below 127 mmHg.",
            "VERIFICADO",
        ),
        *chunk_page(MEDICAL, 7, "Space motion sickness lasts about 3 days on average.", "TB"),
        *chunk_page(
            STANDARD,
            9,
            "[V2 6079] Crew quarters noise limit is NC-40 in missions longer than 30 days.",
            "VERIFICADO",
        ),
    ]


def source() -> RagKnowledgeSource:
    return RagKnowledgeSource(corpus(), GLOSSARY)


def test_finds_the_one_hour_co2_requirement_from_a_spanish_question() -> None:
    results = source().search("¿Cuál es el límite de CO₂ promedio de una hora?", k=3)

    assert results[0].requirement_ref == "V2 6004"
    assert results[0].page == 5
    assert results[0].document_code == STANDARD
    assert results[0].evidence_state is EvidenceState.VERIFICADO


def test_finds_the_headache_passage_and_keeps_the_evidence_state_of_its_document() -> None:
    results = source().search("¿Por qué me duele la cabeza?", k=3)

    assert results[0].document_code == BRIEF
    assert results[0].evidence_state is EvidenceState.TB


def test_translates_medical_terms_so_a_spanish_question_reaches_english_text() -> None:
    results = source().search("¿Cuánto dura el mareo espacial?", k=3)

    assert results[0].document_code == MEDICAL


def test_an_english_question_also_works() -> None:
    results = source().search("What is hypoxia?", k=3)

    assert results[0].requirement_ref == "V2 6003"


def test_returns_nothing_when_no_passage_is_relevant() -> None:
    assert source().search("¿Cómo cambio el filtro de la esclusa?", k=3) == []


def test_returns_at_most_k_passages() -> None:
    assert len(source().search("CO₂ dolor de cabeza límite promedio", k=1)) == 1


def test_a_very_long_passage_is_shortened_for_the_answer() -> None:
    long_chunk = chunk_page("D", 1, "carbon dioxide " + "filler " * 300, "TB", max_chars=5000)

    results = RagKnowledgeSource(long_chunk, GLOSSARY).search("dióxido de carbono", k=1)

    assert len(results[0].excerpt) <= 500


def test_loads_the_chunks_from_the_index_file(tmp_path: Path) -> None:
    index = tmp_path / "chunks.jsonl"
    JsonlChunkStore(index).add(corpus())

    results = RagKnowledgeSource.from_index(index, GLOSSARY).search("dolor de cabeza", k=1)

    assert results[0].document_code == BRIEF


class RecordingSource:
    def __init__(self, results: list[Citation]) -> None:
        self._results = results
        self.calls = 0

    def search(self, text: str, k: int) -> list[Citation]:
        self.calls += 1
        return self._results


def citation(code: str) -> Citation:
    return Citation(code, None, None, "texto", EvidenceState.DEMO)


def test_falls_back_to_the_demo_source_when_the_rag_finds_nothing() -> None:
    fallback = RecordingSource([citation("DEMO")])
    combined = FallbackKnowledgeSource(RecordingSource([]), fallback)

    assert [c.document_code for c in combined.search("x", 3)] == ["DEMO"]
    assert fallback.calls == 1


def test_does_not_consult_the_fallback_when_the_rag_has_passages() -> None:
    fallback = RecordingSource([citation("DEMO")])
    combined = FallbackKnowledgeSource(RecordingSource([citation("RAG")]), fallback)

    assert [c.document_code for c in combined.search("x", 3)] == ["RAG"]
    assert fallback.calls == 0


def test_the_glossary_is_valid_and_every_entry_has_both_languages() -> None:
    entries = json.loads(GLOSSARY.read_text(encoding="utf-8"))["entries"]

    assert entries
    assert all(entry["es"] and entry["en"] for entry in entries)


def test_the_real_demo_source_can_be_the_fallback() -> None:
    demo = DemoKnowledgeSource.from_file(ROOT / "data" / "knowledge" / "demo_catalog.json")
    combined = FallbackKnowledgeSource(RagKnowledgeSource([], GLOSSARY), demo)

    assert combined.search("dolor de cabeza", 1)[0].document_code == "OCHMO-TB-004 CO₂"
