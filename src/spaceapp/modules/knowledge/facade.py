"""Public read-only facade of the knowledge module (ADR-5)."""

from __future__ import annotations

from spaceapp.modules.knowledge.contracts import CitationDTO
from spaceapp.modules.knowledge.domain.model import Action
from spaceapp.modules.knowledge.ports import KnowledgeSource, PassageSource


class ActionCatalogQuery:
    """Title and description of an action. Used by Missions (dev A)."""

    def __init__(self, source: KnowledgeSource) -> None:
        self._source = source

    def get(self, key: str) -> Action | None:
        return self._source.action(key)


class KnowledgeQuery:
    """Citable passages to answer questions. Used by the assistant (inside this module)."""

    def __init__(self, source: PassageSource) -> None:
        self._source = source

    def search(self, text: str, k: int) -> list[CitationDTO]:
        return [
            CitationDTO(
                document_code=c.document_code,
                requirement_ref=c.requirement_ref,
                page=c.page,
                excerpt=c.excerpt,
                evidence_state=c.evidence_state.value,
            )
            for c in self._source.search(text, k)
        ]
