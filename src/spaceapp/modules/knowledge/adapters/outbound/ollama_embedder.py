"""Embeddings adapter with local Ollama (`/api/embed`). No internet: it uses the container."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

from spaceapp.modules.knowledge.ports import EmbeddingError

DEFAULT_MODEL = "bge-m3"
DEFAULT_URL = "http://127.0.0.1:11434"


class OllamaEmbedder:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_URL,
        batch_size: int = 32,
        timeout_s: float = 120.0,
        keep_alive: str = "30m",
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._batch_size = batch_size
        self._timeout_s = timeout_s
        # Ollama unloads the model after 5 minutes of inactivity; loading it costs about 4 s.
        self._keep_alive = keep_alive
        self._opener = opener

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in the same order. `EmbeddingError` if something fails."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors += self._request(texts[start : start + self._batch_size])
        return vectors

    def _request(self, batch: Sequence[str]) -> list[list[float]]:
        request = urllib.request.Request(
            f"{self._base_url}/api/embed",
            data=json.dumps(
                {"model": self.model, "input": list(batch), "keep_alive": self._keep_alive}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout_s) as response:
                payload = json.load(response)
        except (OSError, ValueError) as error:  # no network, slow or with a reply that is not JSON
            raise EmbeddingError(f"Ollama did not answer ({self._base_url}): {error}") from error

        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != len(batch):
            detail = payload.get("error") if isinstance(payload, dict) else None
            raise EmbeddingError(
                f"Ollama did not return one vector per text: {detail or payload!r}"
            )
        return [[float(value) for value in vector] for vector in embeddings]
