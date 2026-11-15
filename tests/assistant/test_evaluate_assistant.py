"""Evaluation of the whole assistant (n8n + Ollama + RAG) with the RAG questions."""

from __future__ import annotations

from typing import Any

from spaceapp.devtools.evaluate_assistant import Verdict, judge, run
from spaceapp.modules.knowledge.evaluate import EvalCase


def response(
    state: str = "ANSWERED",
    citations: list[dict[str, Any]] | None = None,
    composed_by: str = "n8n",
    degraded: bool = False,
) -> dict[str, Any]:
    return {
        "state": state,
        "composed_by": composed_by,
        "degraded": degraded,
        "citations": citations if citations is not None else [],
    }


def cite(document: str = "DOC-A", excerpt: str = "texto") -> dict[str, Any]:
    return {"document_code": document, "excerpt": excerpt}


def test_an_in_scope_question_hits_when_a_citation_has_the_expected_text() -> None:
    case = EvalCase("q", expected_contains=("3 mmhg",))

    verdict = judge(case, response(citations=[cite(excerpt="The limit is 3 mmHg")]))

    assert verdict.passed is True


def test_it_hits_with_the_expected_document_only() -> None:
    case = EvalCase("q", expected_documents=("DOC-A",))

    assert judge(case, response(citations=[cite("DOC-B"), cite("DOC-A")])).passed is True
    assert judge(case, response(citations=[cite("DOC-B")])).passed is False


def test_only_the_first_three_citations_count() -> None:
    case = EvalCase("q", expected_documents=("DOC-A",))
    citations = [cite("DOC-B"), cite("DOC-C"), cite("DOC-D"), cite("DOC-A")]

    assert judge(case, response(citations=citations)).passed is False


def test_an_in_scope_question_that_got_no_information_is_a_miss() -> None:
    case = EvalCase("q", expected_documents=("DOC-A",))

    assert judge(case, response(state="NO_INFO")).passed is False


def test_a_template_answer_still_counts_if_it_cites_the_right_source() -> None:
    case = EvalCase("q", expected_documents=("DOC-A",))

    verdict = judge(case, response(state="TEMPLATE_ANSWER", citations=[cite()], degraded=True))

    assert verdict.passed is True
    assert verdict.degraded is True


def test_an_out_of_scope_question_passes_only_with_no_information_and_no_citation() -> None:
    case = EvalCase("q", out_of_scope=True)

    assert judge(case, response(state="NO_INFO")).passed is True
    assert judge(case, response(state="ANSWERED", citations=[cite()])).passed is False
    assert judge(case, response(state="NO_INFO", citations=[cite()])).passed is False


def test_the_run_summarizes_hits_leaks_states_and_latency() -> None:
    cases = [
        EvalCase("a", expected_documents=("DOC-A",)),
        EvalCase("b", expected_documents=("DOC-A",)),
        EvalCase("c", out_of_scope=True),
        EvalCase("d", out_of_scope=True),
    ]
    answers = {
        "a": response(citations=[cite()]),
        "b": response(state="NO_INFO"),
        "c": response(state="NO_INFO"),
        "d": response(state="ANSWERED", citations=[cite()]),
    }

    summary = run(cases, lambda question: (answers[question], 2.0))

    assert (summary.in_scope, summary.hits) == (2, 1)
    assert (summary.out_of_scope, summary.leaks) == (2, 1)
    assert summary.states == {"ANSWERED": 2, "NO_INFO": 2}
    assert summary.mean_latency_s == 2.0
    assert summary.misses == ["b"]
    assert summary.leaked == ["d"]


def test_a_verdict_keeps_what_is_needed_to_review_it() -> None:
    verdict = judge(EvalCase("q", out_of_scope=True), response(state="NO_INFO"))

    assert isinstance(verdict, Verdict)
    assert verdict.state == "NO_INFO"
