"""Búsqueda sobre los fragmentos de los PDFs de NASA, con respaldo a la fuente de demostración.

Sin modelo de embeddings: puntúa por términos, ponderados por su rareza, y traduce la pregunta con
un glosario porque los documentos están en inglés. Cuando se decida un modelo multilingüe, este
adaptador es el que se reemplaza (plan, decisión 5).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.domain.glossary import Glossary, terms
from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.ingest.chunking import Chunk
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ports import PassageSource

# Por debajo de este puntaje no hay pasaje: una palabra que está en casi todos los fragmentos no basta.
MIN_SCORE = 1.0
EXCERPT_MAX_CHARS = 500
_QUERY_MIN_LENGTH = 4
_STOPWORDS = frozenset(
    [
        "what",
        "that",
        "this",
        "with",
        "from",
        "have",
        "shall",
        "which",
        "para",
        "como",
        "pero",
        "esta",
        "este",
        "esto",
        "cuando",
        "donde",
        "sobre",
        "entre",
        "desde",
        "hasta",
        "porque",
        "cual",
        "cuales",
        "cuanto",
        "cuanta",
        "quien",
    ]
)


def load_glossary(path: Path) -> Glossary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Glossary([(entry["es"], entry["en"]) for entry in raw["entries"]])


def _shorten(text: str) -> str:
    if len(text) <= EXCERPT_MAX_CHARS:
        return text
    return text[: EXCERPT_MAX_CHARS - 1].rstrip() + "…"


class RagKnowledgeSource:
    def __init__(self, chunks: Sequence[Chunk], glossary_path: Path) -> None:
        self._glossary = load_glossary(glossary_path)
        self._chunks = list(chunks)
        self._terms = [terms(chunk.content) for chunk in self._chunks]
        document_frequency = Counter(term for chunk_terms in self._terms for term in chunk_terms)
        total = len(self._chunks)
        self._idf = {
            term: math.log(1 + (total + 1) / count) for term, count in document_frequency.items()
        }

    @classmethod
    def from_index(cls, index_path: Path, glossary_path: Path) -> RagKnowledgeSource:
        return cls(JsonlChunkStore(index_path).all(), glossary_path)

    def search(self, text: str, k: int) -> list[Citation]:
        """Pasajes citables, del más al menos relevante. Vacío si ninguno pasa el umbral."""
        query = {
            term for term in terms(text, _QUERY_MIN_LENGTH) if term not in _STOPWORDS
        } | self._glossary.expand(text)
        if not self._chunks or not query:
            return []

        scored: list[tuple[float, int]] = []
        for position, chunk_terms in enumerate(self._terms):
            score = sum(self._idf[term] for term in query & chunk_terms)
            if score >= MIN_SCORE:
                scored.append((-score, position))
        scored.sort()

        return [self._citation(self._chunks[position]) for _, position in scored[:k]]

    @staticmethod
    def _citation(chunk: Chunk) -> Citation:
        return Citation(
            document_code=chunk.document_code,
            requirement_ref=chunk.requirement_ref,
            page=chunk.page,
            excerpt=_shorten(chunk.content),
            evidence_state=EvidenceState(chunk.evidence_state),
        )


class FallbackKnowledgeSource:
    """Perfil `jurado`: RAG primero; si falta un pasaje, cae a la fuente de demostración."""

    def __init__(self, primary: PassageSource, fallback: PassageSource) -> None:
        self._primary = primary
        self._fallback = fallback

    def search(self, text: str, k: int) -> list[Citation]:
        found = self._primary.search(text, k)
        return found if found else self._fallback.search(text, k)
