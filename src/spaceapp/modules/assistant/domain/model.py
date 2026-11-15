"""Valores del asistente. Sin dependencias externas."""

from __future__ import annotations

from enum import StrEnum


class AskOutcome(StrEnum):
    ANSWERED = "ANSWERED"
    NO_INFO = "NO_INFO"
    EMPTY_QUESTION = "EMPTY_QUESTION"


class OrchestratorError(RuntimeError):
    """El orquestador (n8n) no respondió bien: caído, lento o con una respuesta inválida."""
