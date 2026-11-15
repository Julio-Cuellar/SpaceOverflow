from __future__ import annotations

import json
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.adapters.outbound.rag_source import (
    EXCERPT_MAX_CHARS,
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
    long_chunk = chunk_page("D", 1, "carbon dioxide " + "filler " * 600, "TB", max_chars=20000)

    results = RagKnowledgeSource(long_chunk, GLOSSARY).search("dióxido de carbono", k=1)

    assert len(results[0].excerpt) <= EXCERPT_MAX_CHARS


def test_the_excerpt_shows_the_part_that_matches_not_just_the_start_of_the_passage() -> None:
    # Caso real: TB-044 p. 9 tiene la cifra al final de un fragmento de ~1200 caracteres.
    text = ("Background about the crew timeline and the duty day. " * 60) + (
        "Motion sickness associated with adaptation can last on average for 3 days."
    )
    chunks = chunk_page("TB-044", 9, text, "TB", max_chars=20000)

    results = RagKnowledgeSource(chunks, GLOSSARY).search("¿Cuánto dura el mareo espacial?", k=1)

    assert "3 days" in results[0].excerpt
    assert len(results[0].excerpt) <= EXCERPT_MAX_CHARS
    assert results[0].excerpt.startswith("…")


def test_the_excerpt_prefers_the_region_with_the_rare_term_over_one_with_common_terms() -> None:
    # Dos términos comunes (cabin, pressure) en una región no deben ganarle a un término raro
    # (diluent) con la cifra en otra: contar términos sin ponderar escondía la cifra.
    common_region = "The cabin pressure is monitored. The cabin pressure sensor is checked. " * 8
    # Texto neutro entre las dos regiones: ninguna ventana del tamaño del extracto cubre ambas.
    neutral = "Crew activities and schedules are planned well ahead of time. " * 40
    rare_region = "The atmosphere shall contain at least 30% diluent gas for crew safety."
    target = chunk_page(
        "STD", 9, common_region + neutral + rare_region, "VERIFICADO", max_chars=20000
    )
    fillers = [
        chunk
        for n in range(6)
        for chunk in chunk_page(
            f"F{n}", 1, "The cabin pressure sensor reading was normal today in the habitat.", "TB"
        )
    ]

    results = RagKnowledgeSource([*fillers, *target], GLOSSARY).search(
        "cabin pressure diluent", k=1
    )

    assert results[0].document_code == "STD"
    assert "30% diluent" in results[0].excerpt


def test_a_question_matching_only_one_incidental_word_gets_no_passage() -> None:
    # Caso real: «Who won the last football world cup?» coincidía solo en «world», dentro de una
    # lista de acrónimos, y recibía una respuesta. Una coincidencia aislada no es una respuesta.
    acronyms = chunk_page(
        "STD",
        275,
        "Video Electronics Standards Association venous gas emboli volatile organic compounds "
        "World Health Organization acronyms and abbreviations used in this standard",
        "VERIFICADO",
    )
    fillers = [
        chunk
        for n in range(3)
        for chunk in chunk_page(
            f"F{n}", 1, "Crew quarters noise limit applies to long missions only.", "TB"
        )
    ]

    results = RagKnowledgeSource([*acronyms, *fillers], GLOSSARY).search(
        "Who won the last football world cup?", k=3
    )

    assert results == []


def test_words_the_glossary_translated_do_not_count_against_the_coverage() -> None:
    # «cabeza» y «duele» ya se tradujeron a «headache»: no son términos sin cubrir.
    chunks = chunk_page(
        "TB", 2, "Headache is the first symptom of high ppCO2 in the cabin air.", "TB"
    )

    results = RagKnowledgeSource(chunks, GLOSSARY).search("¿Por qué me duele la cabeza?", k=1)

    assert [r.document_code for r in results] == ["TB"]


def test_a_short_passage_is_shown_whole_without_ellipsis() -> None:
    chunks = chunk_page("D", 1, "Headache occurs at 2.8 mmHg of ppCO2 in the cabin air.", "TB")

    results = RagKnowledgeSource(chunks, GLOSSARY).search("dolor de cabeza", k=1)

    assert results[0].excerpt == "Headache occurs at 2.8 mmHg of ppCO2 in the cabin air."


def test_loads_the_chunks_from_the_index_file(tmp_path: Path) -> None:
    index = tmp_path / "chunks.jsonl"
    JsonlChunkStore(index).add(corpus())

    results = RagKnowledgeSource.from_index(index, GLOSSARY).search("dolor de cabeza", k=1)

    assert results[0].document_code == BRIEF


def test_a_focused_passage_beats_a_long_list_that_only_mentions_the_term() -> None:
    # Caso real: una tabla de condiciones médicas lista «headache» entre decenas de términos.
    long_list = chunk_page(
        "RISK-TABLE",
        81,
        "Acute radiation syndrome Allergic reaction Altitude sickness Anaphylaxis Back pain "
        "Barotrauma Headache Burns Cardiac dysrhythmia Chest injury Constipation Dehydration "
        "Diarrhea Fatigue Fever Hearing loss Kidney stone Nasal congestion Nausea Skin rash",
        "VERIFICADO",
    )
    focused = chunk_page(
        BRIEF,
        2,
        "Headache is the first symptom of high ppCO2. Headache incidence rises with ppCO2.",
        "TB",
    )

    results = RagKnowledgeSource([*long_list, *focused], GLOSSARY).search(
        "¿Por qué me duele la cabeza?", k=2
    )

    assert results[0].document_code == BRIEF


def test_singular_and_plural_forms_match() -> None:
    chunks = [
        *chunk_page("A", 1, "Adaptation dizziness can last on average for 3 days.", "TB"),
        *chunk_page("B", 1, "Unrelated text about pumps and valves in the cabin.", "TB"),
    ]

    # El glosario traduce «dura» a «lasts»; el texto dice «last».
    results = RagKnowledgeSource(chunks, GLOSSARY).search("¿Cuánto dura el mareo?", k=2)

    assert [r.document_code for r in results] == ["A"]


def test_a_heading_or_an_index_entry_is_never_returned_as_a_passage() -> None:
    chunks = [
        *chunk_page(STANDARD, 2, "[V2 6004], 6.2.2.1/", "VERIFICADO"),
        *chunk_page(STANDARD, 4, "[V2 6004] Nominal Carbon Dioxide Levels", "VERIFICADO"),
        *chunk_page(
            STANDARD,
            53,
            "[V2 6004] The system shall limit the average one-hour carbon dioxide partial "
            "pressure in the habitable volume to no more than 3 mmHg.",
            "VERIFICADO",
        ),
    ]

    results = RagKnowledgeSource(chunks, GLOSSARY).search(
        "¿Cuál es el límite de dióxido de carbono?", k=3
    )

    assert [r.page for r in results] == [53]


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
