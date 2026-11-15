"""Null adapter: no model. The use case answers with the passages, uncomposed."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from spaceapp.modules.knowledge.contracts import CitationDTO


class NullLlmGateway:
    available = False

    def stream(
        self, question: str, passages: Sequence[CitationDTO], alerts: Sequence[str]
    ) -> Iterator[str]:
        return iter(())
