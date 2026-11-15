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
HEADACHE = "¿Por qué me duele la cabeza?"


class FakeLlm:
    """Modelo de prueba: emite tokens, puede tardar o fallar, y registra las llamadas."""

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
            raise RuntimeError("el modelo no responde")
        for token in self._tokens:
            time.sleep(self._delay_s)
            yield token


class FakeAlerts:
    """Solo lectura: el asistente no tiene ningún puerto para cambiar una alerta."""

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
    assert "dolor de cabeza entre 2.8 y 4.5 mmhg" in result.text.lower()
    assert result.citations[0].document_code == "OCHMO-TB-004 CO₂"
    assert result.citations[0].evidence_state == "TB"


def test_mentions_the_active_alert_without_changing_it() -> None:
    assistant, _ = build(alerts=FakeAlerts(["CO₂ alto (Alerta)"]))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert "According to the loaded sources:" in result.text
    assert "Active alert: CO₂ alto (Alerta)" in result.text
    assert "does not change the alert" in result.text


def test_a_model_answer_with_a_figure_the_passages_do_not_have_is_replaced_by_the_passages() -> (
    None
):
    llm = FakeLlm(tokens=["Headache appears ", "above 9.9 mmHg."])
    assistant, _ = build(llm=llm)

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "plantilla"
    assert "9.9" not in result.text
    assert "2.8" in result.text


def test_a_model_answer_in_spanish_is_replaced_by_the_passages() -> None:
    llm = FakeLlm(tokens=["El dolor de cabeza aparece ", "entre 2.8 y 4.5 mmHg en la cabina."])
    assistant, _ = build(llm=llm)

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "plantilla"
    assert "en la cabina" not in result.text


def test_a_model_answer_that_only_uses_figures_from_the_passages_is_kept() -> None:
    llm = FakeLlm(tokens=["Headache appears ", "between 2.8 and 4.5 mmHg."])
    assistant, _ = build(llm=llm)

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "llm"
    assert result.text.startswith("Headache appears between 2.8 and 4.5 mmHg.")


def test_answers_no_information_without_calling_the_model_when_no_passage_is_relevant() -> None:
    llm = FakeLlm(tokens=["esto no debe salir"])
    assistant, _ = build(llm=llm)

    result = assistant(uuid.uuid4(), "¿Cómo cambio el filtro de la esclusa?")

    assert result.outcome is AskOutcome.NO_INFO
    assert result.text == NO_INFO_TEXT
    assert result.citations == ()
    assert llm.calls == []


def test_uses_the_models_text_when_it_answers_in_time_and_keeps_the_citations() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["Ventila ", "la zona."]))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "llm"
    assert result.text.startswith("Ventila la zona.")
    assert result.citations[0].document_code == "OCHMO-TB-004 CO₂"


def test_falls_back_to_the_passages_when_the_model_exceeds_the_time_limit() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["tarde", "muy tarde"], delay_s=0.5), timeout_s=0.05)

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "plantilla"
    assert "dolor de cabeza entre 2.8 y 4.5 mmhg" in result.text.lower()


def test_falls_back_to_the_passages_when_the_model_fails() -> None:
    assistant, _ = build(llm=FakeLlm(fail=True))

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "plantilla"
    assert result.outcome is AskOutcome.ANSWERED


def test_works_without_any_language_model() -> None:
    assistant, _ = build(llm=NullLlmGateway())

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.composed_by == "plantilla"
    assert result.citations


def test_streams_the_model_tokens_to_the_caller_in_order() -> None:
    assistant, _ = build(llm=FakeLlm(tokens=["Te ", "recomiendo ", "ventilar."]))
    received: list[str] = []

    assistant(uuid.uuid4(), HEADACHE, on_token=received.append)

    assert received == ["Te ", "recomiendo ", "ventilar."]


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

    assistant(uuid.uuid4(), "¿Cómo cambio el filtro de la esclusa?")

    [event] = publisher.events
    assert event.text == NO_INFO_TEXT
    assert event.citations == []


def test_an_empty_question_publishes_nothing() -> None:
    publisher = ListPublisher()
    assistant, _ = build(publisher=publisher)

    assistant(uuid.uuid4(), "  ")

    assert publisher.events == []
