"""Assistant orchestrator: the n8n agent with its tools (RAG and active alerts).

The backend calls the workflow webhook and receives only `{"text": ...}`. The agent's tools come
back to this backend (see `adapters/inbound/rest.py`), which records what was retrieved: this way
the citations do not depend on what the model says it used.
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
            raise OrchestratorError(f"n8n did not answer: {error}") from error
        return _text_of(payload)


def _text_of(payload: bytes) -> str:
    try:
        data = json.loads(payload)
    except ValueError as error:
        raise OrchestratorError("n8n returned something that is not JSON") from error
    text = data.get("text") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise OrchestratorError("n8n did not return a text")
    return text.strip()
