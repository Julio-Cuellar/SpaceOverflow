"""n8n adapter: calls the agent's webhook and validates what comes back."""

from __future__ import annotations

import uuid

import pytest
from fake_n8n import FakeN8n

from spaceapp.modules.assistant.adapters.outbound.n8n import N8nOrchestrator
from spaceapp.modules.assistant.domain.model import OrchestratorError

TURN = uuid.uuid4()
CONVERSATION = uuid.uuid4()


def ask(orchestrator: N8nOrchestrator, alerts: tuple[str, ...] = ()) -> str:
    return orchestrator.answer(TURN, CONVERSATION, "Why do I have a headache?", alerts)


def test_it_posts_the_turn_to_the_webhook_and_returns_the_text() -> None:
    with FakeN8n(body={"text": "Puede ser el CO₂."}) as n8n:
        text = ask(N8nOrchestrator(n8n.url), alerts=("CO₂ alto",))

    assert text == "Puede ser el CO₂."
    [request] = n8n.requests
    assert request["path"] == "/webhook/space-apps-assistant"
    assert request["content_type"] == "application/json"
    assert request["json"] == {
        "turn_id": str(TURN),
        "conversation_id": str(CONVERSATION),
        "question": "Why do I have a headache?",
        "alerts": ["CO₂ alto"],
    }


def test_it_is_available_only_with_a_webhook_url() -> None:
    assert N8nOrchestrator("http://x/webhook/y").available is True
    assert N8nOrchestrator("").available is False


@pytest.mark.parametrize("status", [404, 500, 502])
def test_an_http_error_is_an_orchestrator_error(status: int) -> None:
    with FakeN8n(status=status) as n8n, pytest.raises(OrchestratorError):
        ask(N8nOrchestrator(n8n.url))


@pytest.mark.parametrize(
    "raw",
    [b"no es json", b"[]", b'{"text": 3}', b'{"otra": "cosa"}', b'{"text": "  "}', b""],
)
def test_an_answer_that_is_not_a_non_empty_text_is_an_orchestrator_error(raw: bytes) -> None:
    with FakeN8n(raw=raw) as n8n, pytest.raises(OrchestratorError):
        ask(N8nOrchestrator(n8n.url))


def test_a_slow_n8n_is_cut_at_the_timeout() -> None:
    with FakeN8n(delay_s=2.0) as n8n, pytest.raises(OrchestratorError):
        ask(N8nOrchestrator(n8n.url, timeout_s=0.2))


def test_an_unreachable_n8n_is_an_orchestrator_error() -> None:
    with pytest.raises(OrchestratorError):
        ask(N8nOrchestrator("http://127.0.0.1:1/webhook/nada", timeout_s=1.0))
