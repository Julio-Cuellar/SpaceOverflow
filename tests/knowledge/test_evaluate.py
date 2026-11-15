from __future__ import annotations

import json
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.evaluate import EvalCase, evaluate, load_cases, main
from spaceapp.modules.knowledge.ingest.chunking import chunk_page
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "data" / "knowledge" / "eval_questions.json"
VALIDATION = ROOT / "data" / "knowledge" / "eval_questions_validation.json"


class FakeSearch:
    """Returns what it is told to for each question."""

    def __init__(self, answers: dict[str, list[Citation]]) -> None:
        self._answers = answers

    def search(self, text: str, k: int) -> list[Citation]:
        return self._answers.get(text, [])[:k]


def passage(document: str, text: str = "text") -> Citation:
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


def test_a_case_with_only_expected_text_accepts_any_document_that_has_it() -> None:
    # The Technical Briefs cite the same requirements as the standard: the content matters.
    cases = [EvalCase("q1", expected_contains=("13.5 psi/min",))]

    found = {"q1": [passage("BRIEF", "...shall not exceed 13.5 psi/min.")]}
    not_found = {"q1": [passage("BRIEF", "unrelated")]}

    assert evaluate(FakeSearch(found), cases).hits == 1
    assert evaluate(FakeSearch(not_found), cases).hits == 0


def test_loading_a_case_without_any_expectation_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    path.write_text(json.dumps({"cases": [{"question": "what?"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="without expectation"):
        load_cases(path)


def test_an_out_of_scope_question_must_not_get_any_passage() -> None:
    cases = [EvalCase("capital?", out_of_scope=True), EvalCase("recipe?", out_of_scope=True)]

    result = evaluate(FakeSearch({"recipe?": [passage("DOC-A")]}), cases)

    assert result.answered_out_of_scope == ["recipe?"]


def test_the_result_passes_only_with_enough_hits_and_no_answers_out_of_scope() -> None:
    in_scope = [EvalCase(f"q{i}", expected_documents=("D",)) for i in range(4)]
    answers = {f"q{i}": [passage("D")] for i in range(3)}  # 3 of 4 hits

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
    assert all(c.out_of_scope or c.expected_documents or c.expected_contains for c in cases)
    assert any(c.out_of_scope for c in cases)


def test_the_validation_set_has_in_scope_and_out_of_scope_cases() -> None:
    cases = load_cases(VALIDATION)

    assert any(c.out_of_scope for c in cases)
    assert any(not c.out_of_scope for c in cases)
    assert all(c.out_of_scope or c.expected_documents or c.expected_contains for c in cases)


def test_the_questions_of_both_sets_are_written_in_english() -> None:
    questions = [case.question for case in (*load_cases(QUESTIONS), *load_cases(VALIDATION))]

    assert all(question.isascii() for question in questions)
    assert all(question.endswith("?") for question in questions)


def test_no_question_is_repeated_across_the_two_sets() -> None:
    questions = [case.question for case in (*load_cases(QUESTIONS), *load_cases(VALIDATION))]

    assert len(questions) == len(set(questions))


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
                        {"question": "Why do I have a headache?", "expected_documents": ["DOC"]},
                        {"question": "What is the capital of France?", "out_of_scope": True},
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
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        assert code == 0
        assert "Hits: 1 of 1" in capsys.readouterr().out

    def test_fails_clearly_when_the_questions_file_does_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--questions",
                str(tmp_path / "missing.json"),
            ]
        )

        assert code == 2
        assert "questions file" in capsys.readouterr().err

    def test_fails_clearly_when_there_is_no_index_yet(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(tmp_path / "missing.jsonl"),
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        assert code == 2
        assert "ingestion" in capsys.readouterr().err
