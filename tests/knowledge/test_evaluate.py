from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.evaluate import (
    EvalCase,
    diagnose,
    evaluate,
    load_cases,
    main,
    matches,
)
from spaceapp.modules.knowledge.ingest.chunking import chunk_page
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "data" / "knowledge" / "eval_questions.json"
RESERVED = ROOT / "data" / "knowledge" / "eval_questions_reserved.json"
REAL_INDEX = ROOT / "data" / "knowledge" / "index" / "chunks.jsonl"


class FakeSearch:
    """Returns what it is told for each question."""

    def __init__(self, answers: dict[str, list[Citation]]) -> None:
        self._answers = answers

    def search(self, text: str, k: int) -> list[Citation]:
        return self._answers.get(text, [])[:k]


class ConstantEmbedder:
    """Everything resembles everything: it tests the wiring, not the quality."""

    model = "fake"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


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
    path.write_text(json.dumps({"cases": [{"question": "¿qué?"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="without expectation"):
        load_cases(path)


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
    assert all(c.out_of_scope or c.expected_documents or c.expected_contains for c in cases)
    assert any(c.out_of_scope for c in cases)


def ranked(*documents: str) -> list[Citation]:
    return [passage(document) for document in documents]


def test_records_the_rank_of_the_first_hit_and_derives_recall_and_mrr() -> None:
    cases = [EvalCase(f"q{i}", expected_documents=("A",)) for i in range(4)]
    answers = {
        "q0": ranked("A"),
        "q1": ranked("X", "A"),
        "q2": ranked("X", "X", "X", "X", "A"),
        "q3": ranked("X", "X"),
    }

    result = evaluate(FakeSearch(answers), cases, k=3)

    assert result.ranks == [1, 2, 5, None]
    assert result.recall_at(1) == 0.25
    assert result.recall_at(3) == 0.5
    assert result.recall_at(5) == 0.75
    assert result.hits == 2  # with k=3: the first two
    assert result.mrr == pytest.approx((1 + 1 / 2 + 1 / 5 + 0) / 4)


def test_recall_and_mrr_are_one_when_nothing_is_in_scope() -> None:
    result = evaluate(FakeSearch({}), [EvalCase("off", out_of_scope=True)])

    assert result.recall_at(3) == 1.0
    assert result.mrr == 1.0


@pytest.mark.parametrize(
    ("anchor", "text"),
    [
        ("3035 kcal", "Energy: 3,035 kcal per day"),
        ("3,035 kcal", "Energy: 3035 kcal per day"),
        ("25 µg", "Vitamin D: 25 μg/day"),
        ("below 2.5 mmhg", "BELOW  2.5\nmmHg"),
    ],
)
def test_anchors_ignore_case_spacing_thousands_separators_and_the_micro_sign(
    anchor: str, text: str
) -> None:
    cases = [EvalCase("q", expected_contains=(anchor,))]

    assert evaluate(FakeSearch({"q": [passage("D", text)]}), cases).hits == 1


@pytest.mark.parametrize(
    ("anchor", "text"),
    [("2.5 mmhg", "25 mmHg"), ("3035 kcal", "2,035 kcal"), ("25 mg", "125 mg")],
)
def test_normalising_anchors_does_not_make_different_numbers_match(anchor: str, text: str) -> None:
    cases = [EvalCase("q", expected_contains=(anchor,))]

    assert evaluate(FakeSearch({"q": [passage("D", text)]}), cases).hits == 0


def test_an_expectation_with_alternatives_accepts_any_one_of_them() -> None:
    case = EvalCase("q", expected_contains_any=("3,035 kcal", "12.7 MJ"))

    assert matches(case, "D", "about 12.7 MJ per day")
    assert matches(case, "D", "3035 kcal")
    assert not matches(case, "D", "2,000 kcal")


def test_alternatives_combine_with_required_text() -> None:
    case = EvalCase("q", expected_contains=("energy",), expected_contains_any=("kcal", "MJ"))

    assert matches(case, "D", "Energy: 10 MJ")
    assert not matches(case, "D", "Energy: ten")
    assert not matches(case, "D", "10 MJ of heat")


def test_loading_reads_the_alternatives_and_a_case_with_only_them_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    path.write_text(
        json.dumps({"cases": [{"question": "q", "expected_contains_any": ["a", "b"]}]}),
        encoding="utf-8",
    )

    [case] = load_cases(path)

    assert case.expected_contains_any == ("a", "b")


def test_diagnose_tells_a_ranking_problem_from_a_missing_passage() -> None:
    chunks = chunk_page("DOC", 1, "The daily energy requirement is 3,035 kcal for the crew.", "TB")
    cases = [
        EvalCase("top", expected_contains=("3,035 kcal",)),
        EvalCase("mid", expected_contains=("3,035 kcal",)),
        EvalCase("deep", expected_contains=("3,035 kcal",)),
        EvalCase("never", expected_contains=("3,035 kcal",)),
        EvalCase("absent", expected_contains=("99 widgets",)),
    ]
    hit = passage("DOC", "requirement is 3,035 kcal")
    filler = passage("DOC", "filler")
    answers = {
        "top": [hit],
        "mid": [filler] * 5 + [hit],
        "deep": [filler] * 12 + [hit],
        "never": [filler] * 3,
    }

    found = {d.question: d for d in diagnose(FakeSearch(answers), chunks, cases)}

    assert [found[q].category for q in ("top", "mid", "deep", "never", "absent")] == [
        "top 3",
        "ranks 4 to 10",
        "rank 11 or later",
        "in the index, not retrieved",
        "not in the index",
    ]
    assert found["mid"].rank == 6
    assert found["never"].rank is None
    assert found["absent"].indexed is False


def test_the_reserved_set_is_large_enough_and_every_case_has_a_text_anchor() -> None:
    cases = load_cases(RESERVED)
    in_scope = [c for c in cases if not c.out_of_scope]

    assert len(in_scope) >= 15
    assert sum(c.out_of_scope for c in cases) >= 4
    assert all(c.expected_contains or c.expected_contains_any for c in in_scope)


@pytest.mark.skipif(not REAL_INDEX.exists(), reason="no real index: the PDFs are not versioned")
def test_every_anchor_of_the_reserved_set_exists_in_the_real_index() -> None:
    chunks = JsonlChunkStore(REAL_INDEX).all()

    orphans = [
        case.question
        for case in load_cases(RESERVED)
        if not case.out_of_scope
        and not any(matches(case, chunk.document_code, chunk.content) for chunk in chunks)
    ]

    assert orphans == []


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
        assert "questions" in capsys.readouterr().err

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

    def test_prints_recall_at_several_cutoffs_and_the_mean_reciprocal_rank(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        out = capsys.readouterr().out
        assert "Recall@1: 100%" in out
        assert "@10: 100%" in out
        assert "MRR: 1.00" in out

    def test_the_diagnose_flag_lists_each_case_with_where_it_stands(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--questions",
                str(self.write_questions(tmp_path)),
                "--diagnose",
            ]
        )

        out = capsys.readouterr().out
        assert code == 0
        assert "[top 3] Why do I have a headache?" in out
        assert "Diagnosis:" in out

    def test_says_which_mode_it_evaluated(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--questions",
                str(self.write_questions(tmp_path)),
            ]
        )

        assert "Mode: lexical" in capsys.readouterr().out

    def test_the_hybrid_mode_uses_the_vectors_and_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index = self.build_index(tmp_path)
        chunks = JsonlChunkStore(index).all()
        vectors = tmp_path / "embeddings.json"
        VectorIndex.build("fake", [c.id for c in chunks], [[1.0, 0.0]] * len(chunks)).save(vectors)

        # With a model where everything resembles everything, the out-of-scope question also gets a
        # passage and the exit code is 1: here all that matters is that the hybrid mode is used.
        main(
            [
                "--index",
                str(index),
                "--questions",
                str(self.write_questions(tmp_path)),
                "--mode",
                "hybrid",
                "--vectors",
                str(vectors),
            ],
            embedder=ConstantEmbedder(),
        )

        assert "Mode: hybrid (fake)" in capsys.readouterr().out

    def test_the_hybrid_mode_without_vectors_says_how_to_make_them(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "--index",
                str(self.build_index(tmp_path)),
                "--questions",
                str(self.write_questions(tmp_path)),
                "--mode",
                "hybrid",
                "--vectors",
                str(tmp_path / "no-hay.json"),
            ],
            embedder=ConstantEmbedder(),
        )

        assert code == 2
        assert "ingest.embed" in capsys.readouterr().err
