"""Adaptador de Ollama local. Habla con su API HTTP en streaming (NDJSON)."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from spaceapp.modules.assistant.application.ask import source_label
from spaceapp.modules.knowledge.contracts import CitationDTO

NO_INFO_RULE = "No tengo esa información en las fuentes cargadas."


def build_prompt(question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]) -> str:
    lines = [
        "Responde en español usando SOLO los pasajes siguientes.",
        f"Si ningún pasaje respalda la respuesta, di exactamente: {NO_INFO_RULE}",
        "Pasajes:",
    ]
    lines += [f"- {p.excerpt} ({source_label(p)})" for p in passages]
    if alerts:
        lines.append("Alerta activa (solo para mencionarla, no la cambies): " + "; ".join(alerts))
    lines.append(f"Pregunta: {question}")
    return "\n".join(lines)


class OllamaGateway:
    available = True

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        opener: Callable[[urllib.request.Request], Any] = urllib.request.urlopen,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._opener = opener

    def stream(
        self, question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]
    ) -> Iterator[str]:
        body = json.dumps(
            {
                "model": self._model,
                "prompt": build_prompt(question, passages, alerts),
                "stream": True,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self._opener(request) as response:
            for raw in response:
                line = raw.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    return
