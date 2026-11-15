"""Orquestador del asistente: el agente de n8n con sus herramientas (RAG y alertas activas).

El backend llama al webhook del workflow y recibe solo `{"text": ...}`. Las herramientas del agente
vuelven a este backend (ver `adapters/inbound/rest.py`), que anota lo recuperado: así las citas
no dependen de lo que el modelo diga que usó.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID

from spaceapp.modules.assistant.domain.model import OrchestratorError

DEFAULT_TIMEOUT_S = 30.0


class N8nOrchestrator:
    def __init__(
        self,
        webhook_url: str,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._url = webhook_url
        self._timeout_s = timeout_s
        self._opener = opener

    @property
    def available(self) -> bool:
        return self._url != ""

    def answer(
        self, turn_id: UUID, conversation_id: UUID, question: str, alerts: Sequence[str]
    ) -> str:
        body = json.dumps(
            {
                "turn_id": str(turn_id),
                "conversation_id": str(conversation_id),
                "question": question,
                "alerts": list(alerts),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with self._opener(request, timeout=self._timeout_s) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise OrchestratorError(f"n8n no respondió: {error}") from error
        return _text_of(payload)


def _text_of(payload: bytes) -> str:
    try:
        data = json.loads(payload)
    except ValueError as error:
        raise OrchestratorError("n8n devolvió algo que no es JSON") from error
    text = data.get("text") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise OrchestratorError("n8n no devolvió un texto")
    return text.strip()
