"""Use case: answer a question with cited passages.

Rules of the architecture plan (section 13):
- The answer is composed only from what was retrieved. With no passage, the model is not called
  and the answer says there is no information.
- If the model exceeds the time limit or fails, the answer is the passages as plain text.
- The citations are set by the use case, not by the model. The assistant never changes an alert.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from uuid import UUID

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.assistant.domain.model import AskOutcome
from spaceapp.modules.assistant.ports import (
    ActiveAlerts,
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
    composed_by: str  # "llm" or "template"
    utterance_id: UUID | None = None


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
    ) -> None:
        self._passages = passages
        self._llm = llm
        self._conversations = conversations
        self._alerts = alerts
        self._publisher = publisher
        self._timeout_s = timeout_s
        self._k = k

    def __call__(
        self,
        conversation_id: UUID,
        text: str,
        on_token: Callable[[str], None] | None = None,
    ) -> AskResult:
        question = text.strip()
        if not question:
            return AskResult(AskOutcome.EMPTY_QUESTION, "", (), "template")

        self._conversations.add(conversation_id, "crew", question, ())
        found = tuple(self._passages.search(question, self._k))

        if not found:
            answer = AskResult(AskOutcome.NO_INFO, NO_INFO_TEXT, (), "template")
        else:
            alerts = self._alerts.titles()
            body, composed_by = self._compose(question, found, alerts, on_token)
            answer = AskResult(AskOutcome.ANSWERED, body, found, composed_by)

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

    def _compose(
        self,
        question: str,
        passages: tuple[CitationDTO, ...],
        alerts: list[str],
        on_token: Callable[[str], None] | None,
    ) -> tuple[str, str]:
        if self._llm.available:
            composed = self._stream_within_limit(question, passages, alerts, on_token)
            if composed:
                sources = "Sources: " + "; ".join(source_label(p) for p in passages)
                return f"{composed}\n\n{sources}", "llm"
        return _template(passages, alerts), "template"

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
