"""El asistente con n8n como orquestador: el agente recupera, el backend cita y valida."""

from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.assistant.adapters.outbound.memory import (
    InMemoryConversations,
    ListPublisher,
)
from spaceapp.modules.assistant.adapters.outbound.null_llm import NullLlmGateway
from spaceapp.modules.assistant.application.ask import NO_INFO_TEXT, AskAssistant, AskOutcome
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog
from spaceapp.modules.assistant.domain.model import OrchestratorError
from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.facade import KnowledgeQuery

DEMO_CATALOG = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "demo_catalog.json"
HEADACHE = "¿Por qué me duele la cabeza?"


class FakeAlerts:
    def __init__(self, titles: Sequence[str] = ()) -> None:
        self._titles = list(titles)

    def titles(self) -> list[str]:
        return list(self._titles)


class FakeAgent:
    """Hace lo que haría el agente de n8n: llama a la herramienta de búsqueda y redacta."""

    available = True

    def __init__(
        self,
        log: RetrievalLog,
        *,
        text: str = "Puede deberse al CO₂ alto.",
        search: bool = True,
        fail: bool = False,
        delay_s: float = 0.0,
    ) -> None:
        self._log = log
        self._text = text
        self._search = search
        self._fail = fail
        self._delay_s = delay_s
        self.calls: list[tuple[uuid.UUID, str, tuple[str, ...]]] = []

    def answer(
        self, turn_id: uuid.UUID, conversation_id: uuid.UUID, question: str, alerts: Sequence[str]
    ) -> str:
        self.calls.append((turn_id, question, tuple(alerts)))
        time.sleep(self._delay_s)
        if self._fail:
            raise OrchestratorError("n8n no responde")
        if self._search:
            facade = KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG))
            self._log.record(turn_id, facade.search(question, 3))
        return self._text


def build(agent_factory, alerts=None, timeout_s: float = 5.0):  # type: ignore[no-untyped-def]
    log = RetrievalLog()
    agent = agent_factory(log)
    conversations = InMemoryConversations()
    publisher = ListPublisher()
    assistant = AskAssistant(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        llm=NullLlmGateway(),
        conversations=conversations,
        alerts=alerts or FakeAlerts(),
        publisher=publisher,
        orchestrator=agent,
        retrievals=log,
        orchestrator_timeout_s=timeout_s,
    )
    return assistant, agent, log, publisher


def test_the_answer_is_the_agents_text_with_citations_built_by_the_backend() -> None:
    assistant, _, _, _ = build(lambda log: FakeAgent(log))

    result = assistant(uuid.uuid4(), HEADACHE, turn_id=uuid.uuid4())

    assert result.outcome is AskOutcome.ANSWERED
    assert result.composed_by == "n8n"
    assert result.degraded is False
    assert result.text.startswith("Puede deberse al CO₂ alto.")
    assert "Fuentes: " in result.text
    assert result.citations
    assert any(c.document_code.startswith("OCHMO-TB-004") for c in result.citations)


def test_the_agent_is_told_the_turn_and_the_active_alerts() -> None:
    assistant, agent, _, _ = build(lambda log: FakeAgent(log), alerts=FakeAlerts(["CO₂ alto"]))
    turn = uuid.uuid4()

    assistant(uuid.uuid4(), HEADACHE, turn_id=turn)

    assert agent.calls == [(turn, HEADACHE, ("CO₂ alto",))]


def test_the_turn_is_closed_afterwards_so_late_tool_calls_are_refused() -> None:
    assistant, _, log, _ = build(lambda log: FakeAgent(log))
    turn = uuid.uuid4()

    assistant(uuid.uuid4(), HEADACHE, turn_id=turn)

    assert log.is_open(turn) is False


def test_an_agent_that_retrieved_nothing_is_not_trusted_and_the_template_answers() -> None:
    assistant, _, _, _ = build(lambda log: FakeAgent(log, search=False, text="Invento algo."))

    result = assistant(uuid.uuid4(), HEADACHE, turn_id=uuid.uuid4())

    assert result.outcome is AskOutcome.ANSWERED
    assert result.composed_by == "plantilla"
    assert result.degraded is True
    assert "Invento algo." not in result.text


def test_an_agent_that_retrieved_nothing_for_an_unknown_question_means_no_information() -> None:
    assistant, _, _, publisher = build(lambda log: FakeAgent(log, text="Es París."))

    result = assistant(uuid.uuid4(), "¿Cuál es la capital de Francia?", turn_id=uuid.uuid4())

    assert result.outcome is AskOutcome.NO_INFO
    assert result.text == NO_INFO_TEXT
    assert result.citations == ()
    assert "París" not in publisher.events[0].text


def test_when_n8n_fails_the_template_answers_and_says_it_was_degraded() -> None:
    assistant, _, log, _ = build(lambda log: FakeAgent(log, fail=True))
    turn = uuid.uuid4()

    result = assistant(uuid.uuid4(), HEADACHE, turn_id=turn)

    assert result.outcome is AskOutcome.ANSWERED
    assert result.composed_by == "plantilla"
    assert result.degraded is True
    assert log.is_open(turn) is False


def test_a_slow_n8n_is_cut_at_the_limit_and_the_template_answers() -> None:
    assistant, _, _, _ = build(lambda log: FakeAgent(log, delay_s=1.0), timeout_s=0.1)

    started = time.monotonic()
    result = assistant(uuid.uuid4(), HEADACHE, turn_id=uuid.uuid4())

    assert time.monotonic() - started < 0.9
    assert result.degraded is True
    assert result.composed_by == "plantilla"


def test_a_late_passage_recorded_after_the_cut_is_refused() -> None:
    assistant, _, log, _ = build(lambda log: FakeAgent(log, delay_s=0.5), timeout_s=0.05)
    turn = uuid.uuid4()

    assistant(uuid.uuid4(), HEADACHE, turn_id=turn)
    time.sleep(0.6)  # el hilo del agente termina y trata de registrar lo que recuperó

    assert log.retrieved(turn) == []


def test_without_an_orchestrator_the_assistant_works_as_before_and_is_not_degraded() -> None:
    assistant = AskAssistant(
        passages=KnowledgeQuery(DemoKnowledgeSource.from_file(DEMO_CATALOG)),
        llm=NullLlmGateway(),
        conversations=InMemoryConversations(),
        alerts=FakeAlerts(),
        publisher=ListPublisher(),
    )

    result = assistant(uuid.uuid4(), HEADACHE)

    assert result.outcome is AskOutcome.ANSWERED
    assert result.degraded is False


def test_an_unavailable_orchestrator_is_skipped_without_calling_it() -> None:
    assistant, agent, _, _ = build(lambda log: FakeAgent(log))
    agent.available = False

    result = assistant(uuid.uuid4(), HEADACHE, turn_id=uuid.uuid4())

    assert agent.calls == []
    assert result.composed_by == "plantilla"
    assert result.degraded is False


def test_the_answer_is_published_with_the_citations_of_what_was_retrieved() -> None:
    assistant, _, _, publisher = build(lambda log: FakeAgent(log))

    result = assistant(uuid.uuid4(), HEADACHE, turn_id=uuid.uuid4())

    [event] = publisher.events
    assert event.utterance_id == result.utterance_id
    assert len(event.citations) == len(result.citations)
