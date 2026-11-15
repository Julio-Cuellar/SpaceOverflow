"""Use case: answer a question with cited passages.

Plan rules (section 13):
- It only writes with what was retrieved. Without a passage, the model is not called and the answer
  says there is no information.
- If the model takes longer than the limit or fails, the answer is the passages as plain text.
- Citations are added by the use case, not by the model. The assistant never changes an alert.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from spaceapp.modules.assistant.application.brief import brief
from spaceapp.modules.assistant.application.grounding import unsupported_figures
from spaceapp.modules.assistant.application.language import is_english
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
    # True if there was an orchestrator but it was no use (down, slow or without passages) and it
    # was answered without it.
    degraded: bool = False


def source_label(citation: CitationDTO) -> str:
    requirement = f" · {citation.requirement_ref}" if citation.requirement_ref else ""
    return f"{citation.document_code}{requirement} · {citation.evidence_state}"


def _template(question: str, passages: tuple[CitationDTO, ...], alerts: list[str]) -> str:
    lines = ["According to the loaded sources:"]
    lines += [f"- {brief(p.excerpt, question)}" for p in passages]
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
        """The agent's text and the citations of what it retrieved, or `None` if not to be trusted.

        It is not trusted if it fails, takes longer than the limit or answers without having
        retrieved any passage: a text without a source is not delivered, even if it sounds good.
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
        except Exception:  # down, slow or with an invalid answer: answer without it
            return None
        finally:
            self._retrievals.close(turn_id)
            executor.shutdown(wait=False, cancel_futures=True)
        if not composed or not cited:
            return None
        if not self._acceptable(composed, question, cited, self._alerts.titles()):
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
            if composed and self._acceptable(composed, question, passages, alerts):
                sources = "Sources: " + "; ".join(source_label(p) for p in passages)
                return f"{composed}\n\n{sources}", "llm"
        return _template(question, passages, alerts), "plantilla"

    @classmethod
    def _acceptable(
        cls, text: str, question: str, passages: tuple[CitationDTO, ...], alerts: list[str]
    ) -> bool:
        """In English, not refusing, with figures from the sources; else the passages go out."""
        return (
            is_english(text)
            and not cls._refuses(text)
            and cls._figures_supported(text, question, passages, alerts)
        )

    @staticmethod
    def _refuses(text: str) -> bool:
        """It says it lacks the information although it was given passages: useless as an answer.

        A small model does this even with passages that do answer. Citing sources next to an
        'I don't know' misleads; the literal text of the passages does not.
        """
        return NO_INFO_TEXT.rstrip(".").lower() in text.lower().replace("\u2019", "'")

    @staticmethod
    def _figures_supported(
        text: str, question: str, passages: tuple[CitationDTO, ...], alerts: list[str]
    ) -> bool:
        """Every figure in the wording comes from a passage, the question or an alert.

        If not, it is not delivered: the passages are answered as they are. When in doubt, the
        literal text.
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
        except Exception:  # timeout or any model failure: the passages are returned
            return ""
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        return "".join(pieces).strip()
