from __future__ import annotations

import time
import uuid
from collections.abc import Iterator, Sequence
from pathlib import Path

from spaceapp.modules.assistant.adapters.outbound.memory import (
    InMemoryConversations,
    ListPublisher,
)
from spaceapp.modules.assistant.adapters.outbound.null_llm import NullLlmGateway
from spaceapp.modules.assistant.application.ask import (
    NO_INFO_TEXT,
    AskAssistant,
    AskOutcome,
)
from spaceapp.modules.assistant.ports import LlmGateway
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.contracts import CitationDTO
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
HEADACHE = "Why do I have a headache?"


class FakeLlm:
    """Test model: emits tokens, can be slow or fail, and records the calls."""

    available = True

    def __init__(
        self, tokens: Sequence[str] = (), delay_s: float = 0.0, fail: bool = False
    ) -> None:
        self._tokens = tokens
        self._delay_s = delay_s
        self._fail = fail
        self.calls: list[tuple[str, tuple[CitationDTO, ...], tuple[str, ...]]] = []

    def stream(
        self, question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]
    ) -> Iterator[str]:
        self.calls.append((question, tuple(passages), tuple(alerts)))
        if self._fail:
            raise RuntimeError("the model does not respond")
        for token in self._tokens:
            time.sleep(self._delay_s)
            yield token


class FakeAlerts:
    """Read-only: the assistant has no port to change an alert."""

    def __init__(self, titles: Sequence[str] = ()) -> None:
        self._titles = list(titles)

    def titles(self) -> list[str]:
        return list(self._titles)


def build(
    llm: LlmGateway | None = None,
    alerts: FakeAlerts | None = None,
    timeout_s: float = 8.0,
    publisher: ListPublisher | None = None,
) -> tuple[AskAssistant, InMemoryConversations]:
    conversations = InMemoryConversations()
    assistant = AskAssistant(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        llm=llm or NullLlmGateway(),
        conversations=conversations,
        alerts=alerts or FakeAlerts(),
        publisher=publisher or ListPublisher(),
        timeout_s=timeout_s,
    )
    return assistant, conversations


def test_answers_a_headache_question_with_the_tb004_passage_and_its_citation() -> None:
    assistant, _ = build()

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.outcome is AskOutcome.ANSWERED
    assert "headache between 2.8 and 4.5 mmhg" in result.text.lower()
    assert result.citations[0].document_code == "OCHMO-TB-004 CO₂"
    assert result.citations[0].evidence_state == "TB"


def test_mentions_the_active_alert_without_changing_it() -> None:
    assistant, _ = build(alerts=FakeAlerts(["High CO₂ (Alert)"]))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert "Active alert: High CO₂ (Alert)" in result.text
    assert "does not change the alert" in result.text


def test_answers_no_information_without_calling_the_model_when_no_passage_is_relevant() -> None:
    llm = FakeLlm(tokens=["this must not come out"])
    assistant, _ = build(llm=llm)

    result = assistant(uuid.uuid4(), "How do I change the airlock filter?")

    assert result.outcome is AskOutcome.NO_INFO
    assert result.text == NO_INFO_TEXT
    assert result.citations == ()
    assert llm.calls == []


def test_uses_the_models_text_when_it_answers_in_time_and_keeps_the_citations() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["Ventilate ", "the zone."]))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "llm"
    assert result.text.startswith("Ventilate the zone.")
    assert result.citations[0].document_code == "OCHMO-TB-004 CO₂"


def test_falls_back_to_the_passages_when_the_model_exceeds_the_time_limit() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["late", "very late"], delay_s=0.5), timeout_s=0.05)

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "template"
    assert "headache between 2.8 and 4.5 mmhg" in result.text.lower()


def test_falls_back_to_the_passages_when_the_model_fails() -> None:
    assistant, _ = build(llm=FakeLlm(fail=True))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "template"
    assert result.outcome is AskOutcome.ANSWERED


def test_works_without_any_language_model() -> None:
    assistant, _ = build(llm=NullLlmGateway())

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "template"
    assert result.citations


def test_streams_the_model_tokens_to_the_caller_in_order() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["I ", "recommend ", "ventilating."]))
    received: list[str] = []

    assistant(uuid.uuid4(), HEADACHE, on_token=received.append)

    assert received == ["I ", "recommend ", "ventilating."]


def test_an_empty_question_is_refused_and_nothing_is_stored() -> None:
    assistant, conversations = build()
    conversation = uuid.uuid4()

    result = assistant(conversation, "   ")

    assert result.outcome is AskOutcome.EMPTY_QUESTION
    assert conversations.messages(conversation) == []


def test_stores_the_question_and_the_answer_in_the_conversation() -> None:
    assistant, conversations = build()
    conversation = uuid.uuid4()

    assistant(conversation, HEADACHE)

    assert [m.role for m in conversations.messages(conversation)] == ["crew", "assistant"]
    assert conversations.messages(conversation)[0].text == HEADACHE


def test_publishes_answer_ready_with_the_utterance_id_text_and_citations() -> None:
    publisher = ListPublisher()
    assistant, conversations = build(publisher=publisher)
    conversation = uuid.uuid4()

    result = assistant(conversation, HEADACHE)

    [event] = publisher.events
    assert result.utterance_id == conversations.messages(conversation)[1].id
    assert event.utterance_id == result.utterance_id
    assert event.text == result.text
    assert [c.document_code for c in event.citations] == [c.document_code for c in result.citations]


def test_publishes_the_no_information_answer_too_with_no_citations() -> None:
    publisher = ListPublisher()
    assistant, _ = build(publisher=publisher)

    assistant(uuid.uuid4(), "How do I change the airlock filter?")

    [event] = publisher.events
    assert event.text == NO_INFO_TEXT
    assert event.citations == []


def test_an_empty_question_publishes_nothing() -> None:
    publisher = ListPublisher()
    assistant, _ = build(publisher=publisher)

    assistant(uuid.uuid4(), "  ")

    assert publisher.events == []
