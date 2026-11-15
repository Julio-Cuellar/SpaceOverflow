from __future__ import annotations

import json
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.adapters.outbound.rag_source import load_glossary
from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.evaluate import EvalCase, evaluate, load_cases, main
from spaceapp.modules.knowledge.ingest.chunking import chunk_page
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "data" / "knowledge" / "eval_questions.json"
GLOSSARY = ROOT / "data" / "knowledge" / "glossary_es_en.json"


class FakeSearch:
    """Devuelve lo que se le indique para cada pregunta."""

    def __init__(self, answers: dict[str, list[Citation]]) -> None:
        self._answers = answers

    def search(self, text: str, k: int) -> list[Citation]:
        return self._answers.get(text, [])[:k]


def passage(document: str, text: str = "texto") -> Citation:
    return Citation(document, None, 1, text, EvidenceState.TB)


def test_counts_a_hit_when_the_expected_document_is_among_the_top_results() -> None:
    cases = [EvalCase("q1", expected_documents=("DOC-A",))]

    result = evaluate(FakeSearch({"q1": [passage("DOC-B"), passage("DOC-A")]}), cases)

    assert result.hits == 1
    assert result.hit_rate == 1.0
    assert result.misses == []


def test_a_document_outside_the_top_k_is_a_miss() -> None:
    cases = [EvalCase("q1", expected_documents=("DOC-A",))]
    ranked = [passage("DOC-B"), passage("DOC-C"), passage("DOC-D"), passage("DOC-A")]

    result = evaluate(FakeSearch({"q1": ranked}), cases, k=3)

    assert result.hits == 0
    assert result.misses == ["q1"]


def test_any_of_several_acceptable_documents_counts() -> None:
    cases = [EvalCase("q1", expected_documents=("DOC-A", "DOC-B"))]

    assert evaluate(FakeSearch({"q1": [passage("DOC-B")]}), cases).hits == 1


def test_a_case_can_also_require_text_in_the_passage() -> None:
    cases = [EvalCase("q1", expected_documents=("DOC-A",), expected_contains=("3 mmhg",))]
    right = {"q1": [passage("DOC-A", "The limit is 3 mmHg")]}
    wrong = {"q1": [passage("DOC-A", "Unrelated text")]}

    assert evaluate(FakeSearch(right), cases).hits == 1
    assert evaluate(FakeSearch(wrong), cases).hits == 0


def test_an_out_of_scope_question_must_not_get_any_passage() -> None:
    cases = [EvalCase("capital?", out_of_scope=True), EvalCase("recipe?", out_of_scope=True)]

    result = evaluate(FakeSearch({"recipe?": [passage("DOC-A")]}), cases)

    assert result.answered_out_of_scope == ["recipe?"]


def test_the_result_passes_only_with_enough_hits_and_no_answers_out_of_scope() -> None:
    in_scope = [EvalCase(f"q{i}", expected_documents=("D",)) for i in range(4)]
    answers = {f"q{i}": [passage("D")] for i in range(3)}  # 3 de 4 aciertos

    result = evaluate(FakeSearch(answers), in_scope)
    assert result.passed(min_hit_rate=0.75)
    assert not result.passed(min_hit_rate=0.9)

    with_leak = evaluate(
        FakeSearch({**answers, "off": [passage("D")]}),
        [*in_scope, EvalCase("off", out_of_scope=True)],
    )
    assert not with_leak.passed(min_hit_rate=0.5)


def test_the_real_question_set_has_about_fifteen_cases_with_a_clear_expectation() -> None:
    cases = load_cases(QUESTIONS)

    assert len(cases) >= 15
    assert all(c.out_of_scope or c.expected_documents for c in cases)
    assert any(c.out_of_scope for c in cases)


def test_the_glossary_translates_something_in_every_question_of_the_set() -> None:
    glossary = load_glossary(GLOSSARY)

    untranslated = [
        case.question
        for case in load_cases(QUESTIONS)
        if not case.out_of_scope and not glossary.expand(case.question)
    ]

    assert untranslated == []


def test_the_out_of_scope_questions_get_no_translation_so_they_cannot_match() -> None:
    glossary = load_glossary(GLOSSARY)

    for case in load_cases(QUESTIONS):
        if case.out_of_scope:
            assert not glossary.expand(case.question), case.question


class TestCommand:
    def build_index(self, tmp_path: Path) -> Path:
        index = tmp_path / "chunks.jsonl"
        JsonlChunkStore(index).add(
            chunk_page("DOC", 1, "Headache can occur between 2.8 and 4.5 mmHg of ppCO2.", "TB")
        )
        return index

    def write_questions(self, tmp_path: Path) -> Path:
        path = tmp_path / "questions.json"
        path.write_text(
            json.dumps(
                {
                    "cases": [
                        {"question": "¿Por qué me duele la cabeza?", "expected_documents": ["DOC"]},
                        {"question": "¿Cuál es la capital de Francia?", "out_of_scope": True},
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_passes_when_the_expected_passages_are_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--glossary",
                str(GLOSSARY),
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        assert code == 0
        assert "Aciertos: 1 de 1" in capsys.readouterr().out

    def test_fails_clearly_when_there_is_no_index_yet(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(tmp_path / "no-existe.jsonl"),
                "--glossary",
                str(GLOSSARY),
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        assert code == 2
        assert "ingesta" in capsys.readouterr().err
