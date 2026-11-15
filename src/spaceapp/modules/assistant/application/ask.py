"""Caso de uso: responder una pregunta con pasajes citados.

Reglas del plan (sección 13):
- Solo se redacta con lo recuperado. Sin pasaje, no se llama al modelo y se dice que no hay
  información.
- Si el modelo tarda más del límite o falla, se responde con los pasajes en texto plano.
- Las citas las pone el caso de uso, no el modelo. El asistente no cambia ninguna alerta.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from spaceapp.modules.assistant.application.grounding import unsupported_figures
from spaceapp.modules.assistant.application.retrieval_log import RetrievalLog
from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.assistant.domain.model import AskOutcome
from spaceapp.modules.assistant.ports import (
    ActiveAlerts,
    AssistantOrchestrator,
    ConversationRepository,
    EventPublisher,
    LlmGateway,
    PassageSearch,
)
from spaceapp.modules.knowledge.contracts import CitationDTO

__all__ = ["NO_INFO_TEXT", "AskAssistant", "AskOutcome", "AskResult", "source_label"]

NO_INFO_TEXT = "I don't have that information in the loaded sources."
ALERT_NOTE = "This answer does not change the alert."
TOP_K = 3
TIMEOUT_S = 8.0


@dataclass(frozen=True)
class AskResult:
    outcome: AskOutcome
    text: str
    citations: tuple[CitationDTO, ...]
    composed_by: str  # "n8n", "llm" o "plantilla"
    utterance_id: UUID | None = None
    # True si había orquestador pero no sirvió (caído, lento o sin pasajes) y se respondió sin él.
    degraded: bool = False


def source_label(citation: CitationDTO) -> str:
    requirement = f" · {citation.requirement_ref}" if citation.requirement_ref else ""
    return f"{citation.document_code}{requirement} · {citation.evidence_state}"


def _template(passages: tuple[CitationDTO, ...], alerts: list[str]) -> str:
    lines = ["According to the loaded sources:"]
    lines += [f"- {p.excerpt} ({source_label(p)})" for p in passages]
    lines += [f"Active alert: {title}. {ALERT_NOTE}" for title in alerts]
    return "\n".join(lines)


class AskAssistant:
    def __init__(
        self,
        *,
        passages: PassageSearch,
        llm: LlmGateway,
        conversations: ConversationRepository,
        alerts: ActiveAlerts,
        publisher: EventPublisher,
        timeout_s: float = TIMEOUT_S,
        k: int = TOP_K,
        orchestrator: AssistantOrchestrator | None = None,
        retrievals: RetrievalLog | None = None,
        orchestrator_timeout_s: float = 30.0,
    ) -> None:
        self._passages = passages
        self._llm = llm
        self._conversations = conversations
        self._alerts = alerts
        self._publisher = publisher
        self._timeout_s = timeout_s
        self._k = k
        self._orchestrator = orchestrator
        self._retrievals = retrievals
        self._orchestrator_timeout_s = orchestrator_timeout_s

    def __call__(
        self,
        conversation_id: UUID,
        text: str,
        on_token: Callable[[str], None] | None = None,
        turn_id: UUID | None = None,
    ) -> AskResult:
        question = text.strip()
        if not question:
            return AskResult(AskOutcome.EMPTY_QUESTION, "", (), "plantilla")

        self._conversations.add(conversation_id, "crew", question, ())

        via = None
        degraded = False
        if (
            self._orchestrator is not None
            and self._orchestrator.available
            and self._retrievals is not None
        ):
            via = self._via_orchestrator(turn_id or uuid4(), conversation_id, question)
            degraded = via is None

        if via is not None:
            body, cited = via
            answer = AskResult(AskOutcome.ANSWERED, body, cited, "n8n")
        else:
            found = tuple(self._passages.search(question, self._k))
            if not found:
                answer = AskResult(AskOutcome.NO_INFO, NO_INFO_TEXT, (), "plantilla")
            else:
                alerts = self._alerts.titles()
                body, composed_by = self._compose(question, found, alerts, on_token)
                answer = AskResult(AskOutcome.ANSWERED, body, found, composed_by, degraded=degraded)

        utterance_id = self._conversations.add(
            conversation_id, "assistant", answer.text, answer.citations
        )
        answer = replace(answer, utterance_id=utterance_id)
        self._publisher.publish(
            AnswerReady(
                utterance_id=utterance_id, text=answer.text, citations=list(answer.citations)
            )
        )
        return answer

    def _via_orchestrator(
        self, turn_id: UUID, conversation_id: UUID, question: str
    ) -> tuple[str, tuple[CitationDTO, ...]] | None:
        """Texto del agente y las citas de lo que recuperó, o `None` si no hay que fiarse de él.

        No se fía si falla, tarda más del límite o contesta sin haber recuperado ningún pasaje:
        un texto sin fuente no se entrega, aunque suene bien.
        """
        assert self._orchestrator is not None and self._retrievals is not None
        self._retrievals.open(turn_id)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self._orchestrator.answer, turn_id, conversation_id, question, self._alerts.titles()
        )
        try:
            composed = future.result(timeout=self._orchestrator_timeout_s).strip()
            cited = tuple(self._retrievals.retrieved(turn_id))
        except Exception:  # caído, lento o con una respuesta inválida: se responde sin él
            return None
        finally:
            self._retrievals.close(turn_id)
            executor.shutdown(wait=False, cancel_futures=True)
        if not composed or not cited:
            return None
        if not self._figures_supported(composed, question, cited, self._alerts.titles()):
            return None
        sources = "Sources: " + "; ".join(source_label(p) for p in cited)
        return f"{composed}\n\n{sources}", cited

    def _compose(
        self,
        question: str,
        passages: tuple[CitationDTO, ...],
        alerts: list[str],
        on_token: Callable[[str], None] | None,
    ) -> tuple[str, str]:
        if self._llm.available:
            composed = self._stream_within_limit(question, passages, alerts, on_token)
            if composed and self._figures_supported(composed, question, passages, alerts):
                sources = "Sources: " + "; ".join(source_label(p) for p in passages)
                return f"{composed}\n\n{sources}", "llm"
        return _template(passages, alerts), "plantilla"

    @staticmethod
    def _figures_supported(
        text: str, question: str, passages: tuple[CitationDTO, ...], alerts: list[str]
    ) -> bool:
        """Toda cifra de la redacción sale de un pasaje, de la pregunta o de una alerta.

        Si no, no se entrega: se responde con los pasajes tal cual. Ante la duda, el texto literal.
        """
        sources = [
            question,
            *alerts,
            *(f"{p.excerpt} {p.requirement_ref or ''} {p.document_code}" for p in passages),
        ]
        return not unsupported_figures(text, *sources)

    def _stream_within_limit(
        self,
        question: str,
        passages: tuple[CitationDTO, ...],
        alerts: list[str],
        on_token: Callable[[str], None] | None,
    ) -> str:
        pieces: list[str] = []

        def run() -> None:
            for token in self._llm.stream(question, passages, alerts):
                pieces.append(token)
                if on_token is not None:
                    on_token(token)

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run)
        try:
            future.result(timeout=self._timeout_s)
        except Exception:  # tiempo agotado o cualquier fallo del modelo: se devuelven los pasajes
            return ""
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        return "".join(pieces).strip()
