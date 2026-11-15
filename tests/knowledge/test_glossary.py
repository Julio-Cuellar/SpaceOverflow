from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.adapters.outbound.rag_source import load_glossary
from spaceapp.modules.knowledge.domain.glossary import Glossary, terms, token_counts, words
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY_FILE = ROOT / "data" / "knowledge" / "glossary_es_en.json"
REAL_INDEX = ROOT / "data" / "knowledge" / "index" / "chunks.jsonl"


def test_plural_endings_are_ignored_so_singular_and_plural_match() -> None:
    assert terms("lasts days headaches") == {"last", "day", "headache"}


def test_words_that_end_in_ss_or_are_short_are_left_alone() -> None:
    assert terms("stress pressure gas") == {"stress", "pressure", "gas"}


def test_token_counts_keep_the_frequency_of_each_term() -> None:
    assert token_counts("headache headache fatigue") == Counter({"headache": 2, "fatigue": 1})


def test_explain_returns_the_translation_and_the_spanish_words_it_consumed() -> None:
    glossary = Glossary([(["dolor de cabeza", "duele"], ["headache"])])

    english, consumed = glossary.explain("¿Por qué me duele la cabeza? Me duele mucho")

    assert english == {"headache"}
    assert "duele" in consumed


def test_explain_consumes_nothing_when_no_phrase_matches() -> None:
    assert Glossary([(["dura"], ["lasts"])]).explain("¿Cuánto cuesta?") == (
        frozenset(),
        frozenset(),
    )


def test_the_glossary_expansion_is_normalized_the_same_way() -> None:
    glossary = Glossary([(["dura"], ["lasts"])])

    assert glossary.expand("¿Cuánto dura?") == {"last"}


def test_every_spanish_key_is_written_already_normalized() -> None:
    # Without accents and in lowercase: otherwise the phrase never matches the normalized question.
    entries = json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))["entries"]

    not_normalized = [
        phrase for entry in entries for phrase in entry["es"] if phrase != " ".join(words(phrase))
    ]

    assert not_normalized == []


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("¿Cuánta energía diaria necesita un astronauta?", "energy"),
        ("¿Cuántas calorías por hora?", "kcal"),
        ("¿Cuánta vitamina D se necesita al día?", "vitamin"),
        ("¿Cuánto calcio y sodio se recomienda?", "calcium"),
        ("¿Qué porcentaje de gas diluyente se exige?", "diluent"),
        ("¿Cuánto nitrógeno hay en la cabina?", "nitrogen"),
        ("¿Qué se exige en una actividad extravehicular?", "extravehicular"),
        ("¿Cómo es el traje espacial?", "spacesuit"),
        ("¿Qué fuerza muscular debe mantenerse?", "muscle"),
        ("¿Qué densidad ósea debe conservar?", "bone"),
        ("¿Cuál es el límite de ruido de una alarma?", "alarm"),
        ("¿Qué iluminación necesita la tripulación?", "lighting"),
        ("¿Cuál es el límite de dosis por evento de partículas solares?", "solar"),
        ("¿Cómo se trata una lesión?", "injury"),
        ("¿Cuál es la presión parcial de oxígeno?", "partial"),
        ("¿Cuánto cambia la presión total?", "total"),
    ],
)
def test_the_glossary_covers_the_main_topics_of_the_standard(question: str, expected: str) -> None:
    english = load_glossary(GLOSSARY_FILE).expand(question)

    assert expected in english


@pytest.mark.skipif(not REAL_INDEX.exists(), reason="sin índice real: los PDFs no se versionan")
def test_every_english_term_of_the_glossary_exists_in_the_real_index() -> None:
    # A translation to a word that no document has is no use to find anything.
    vocabulary: set[str] = set()
    for chunk in JsonlChunkStore(REAL_INDEX).all():
        vocabulary |= terms(chunk.content, 1)
    entries = json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))["entries"]

    dead = sorted(
        {
            f"{translation}→{term}"
            for entry in entries
            for translation in entry["en"]
            for term in terms(translation, 1)
            if term not in vocabulary
        }
    )

    assert dead == []
