"""Values of the assistant. No external dependencies."""

from __future__ import annotations

from enum import StrEnum


class AskOutcome(StrEnum):
    ANSWERED = "ANSWERED"
    NO_INFO = "NO_INFO"
    EMPTY_QUESTION = "EMPTY_QUESTION"


class OrchestratorError(RuntimeError):
    """The orchestrator (n8n) did not answer well: down, slow or with an invalid answer."""
