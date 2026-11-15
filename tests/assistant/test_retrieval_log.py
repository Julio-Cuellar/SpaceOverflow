"""Record of what the agent retrieved in a turn: the citations come from it, not from the model."""

from __future__ import annotations

import uuid

import pytest

from spaceapp.modules.assistant.application.retrieval_log import (
    RetrievalLog,
    TurnClosedError,
    passage_id,
)
from spaceapp.platform.vocab import Citation


def citation(
    excerpt: str = "ppCO2 promedio de 1 h ≤ 3 mmHg", ref: str | None = "V2 6004"
) -> Citation:
    return Citation(
        document_code="NASA-STD-3001 Vol. 2 Rev F",
        requirement_ref=ref,
        page=44,
        excerpt=excerpt,
        evidence_state="VERIFIED",
    )


def test_the_passage_id_is_stable_and_depends_on_the_content() -> None:
    assert passage_id(citation()) == passage_id(citation())
    assert passage_id(citation()) != passage_id(citation("other text"))
    assert passage_id(citation()) != passage_id(citation(ref=None))


def test_it_records_what_the_agent_retrieved_in_order_without_repeating() -> None:
    log = RetrievalLog()
    turn = uuid.uuid4()
    log.open(turn)

    log.record(turn, [citation("a"), citation("b")])
    log.record(turn, [citation("b"), citation("c")])

    assert [c.excerpt for c in log.retrieved(turn)] == ["a", "b", "c"]


def test_recording_returns_the_ids_the_agent_will_see() -> None:
    log = RetrievalLog()
    turn = uuid.uuid4()
    log.open(turn)

    ids = log.record(turn, [citation("a")])

    assert ids == [passage_id(citation("a"))]


def test_a_turn_that_was_never_opened_cannot_record() -> None:
    with pytest.raises(TurnClosedError):
        RetrievalLog().record(uuid.uuid4(), [citation()])


def test_a_closed_turn_rejects_late_tool_calls() -> None:
    log = RetrievalLog()
    turn = uuid.uuid4()
    log.open(turn)
    log.close(turn)

    assert log.is_open(turn) is False
    with pytest.raises(TurnClosedError):
        log.record(turn, [citation()])


def test_closing_forgets_the_turn_so_nothing_is_kept() -> None:
    log = RetrievalLog()
    turn = uuid.uuid4()
    log.open(turn)
    log.record(turn, [citation()])
    log.close(turn)

    assert log.retrieved(turn) == []


def test_turns_do_not_see_each_others_passages() -> None:
    log = RetrievalLog()
    first, second = uuid.uuid4(), uuid.uuid4()
    log.open(first)
    log.open(second)

    log.record(first, [citation("only from the first")])

    assert log.retrieved(second) == []
