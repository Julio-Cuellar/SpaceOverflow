"""Búsqueda sobre los fragmentos de los PDFs de NASA, con respaldo a la fuente de demostración.

Sin modelo de embeddings: puntúa por términos, ponderados por su rareza, y traduce la pregunta con
un glosario porque los documentos están en inglés. Cuando se decida un modelo multilingüe, este
adaptador es el que se reemplaza (plan, decisión 5).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.domain.glossary import (
    Glossary,
    content_word_count,
    stem,
    terms,
    token_counts,
)
from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.ingest.chunking import MAX_CHARS, Chunk
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ports import PassageSource

# Por debajo de este puntaje no hay pasaje: una palabra presente en casi todos los fragmentos no
# basta.
MIN_SCORE = 1.0
MIN_MATCHED_TERMS = 2
# Por debajo de este número de palabras, un fragmento es un título o una entrada de índice.
MIN_CONTENT_WORDS = 6
BM25_K1 = 1.5
BM25_B = 0.75
# Se cita el fragmento completo: recortar a 500 caracteres escondía la cifra en la mitad de los
# casos
# (medido sobre los PDFs reales: con 500 se veía 7 de 25 respuestas; con 1200, 13 de 25).
EXCERPT_MAX_CHARS = MAX_CHARS
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


_WORD = re.compile(r"[a-z0-9]+")
_CONTEXT_BEFORE = 120


def _snippet(content: str, query: set[str], idf: dict[str, float]) -> str:
    """Extracto de hasta 500 caracteres: la parte del pasaje que mejor cubre la pregunta.

    Recortar siempre el comienzo escondería la cifra cuando está al final de un fragmento largo.
    Cada término cuenta por su rareza: un término raro («diluent») pesa más que dos comunes
    («cabin», «pressure»), que aparecen por todas partes y no señalan dónde está la respuesta.
    """
    if len(content) <= EXCERPT_MAX_CHARS:
        return content

    lowered = content.lower()
    start = 0
    best = -1.0
    for match in _WORD.finditer(lowered):
        if stem(match.group()) not in query:
            continue
        candidate = max(0, match.start() - _CONTEXT_BEFORE)
        window = lowered[candidate : candidate + EXCERPT_MAX_CHARS]
        covered = sum(
            idf.get(term, 0.0) for term in {stem(w) for w in _WORD.findall(window)} & query
        )
        if covered > best:
            best, start = covered, candidate

    width = EXCERPT_MAX_CHARS - 2  # queda sitio para las elipsis
    if start > 0:
        space = content.find(" ", start)
        if 0 <= space < start + 40:
            start = space + 1  # no empezar a media palabra
    piece = content[start : start + width]
    truncated = start + width < len(content)
    if truncated:
        cut = piece.rfind(" ")
        if cut > width // 2:
            piece = piece[:cut]
    return ("…" if start > 0 else "") + piece.strip() + ("…" if truncated else "")


class RagKnowledgeSource:
    def __init__(self, chunks: Sequence[Chunk], glossary_path: Path) -> None:
        self._glossary = load_glossary(glossary_path)
        # Los títulos sueltos y las entradas de índice no son pasajes citables: se descartan.
        self._chunks = [c for c in chunks if content_word_count(c.content) >= MIN_CONTENT_WORDS]
        self._counts = [token_counts(chunk.content) for chunk in self._chunks]
        self._lengths = [sum(counts.values()) for counts in self._counts]
        self._average_length = (sum(self._lengths) / len(self._lengths)) if self._lengths else 1.0
        document_frequency = Counter(term for counts in self._counts for term in counts)
        total = len(self._chunks)
        self._idf = {
            term: math.log(1 + (total + 1) / count) for term, count in document_frequency.items()
        }

    def _score(self, query: set[str], position: int) -> float:
        """BM25: pondera cada término por su rareza, su frecuencia y la longitud del fragmento."""
        counts = self._counts[position]
        length_ratio = self._lengths[position] / self._average_length
        score = 0.0
        for term in query & counts.keys():
            frequency = counts[term]
            saturation = (
                frequency
                * (BM25_K1 + 1)
                / (frequency + BM25_K1 * (1 - BM25_B + BM25_B * length_ratio))
            )
            score += self._idf[term] * saturation
        return score

    @classmethod
    def from_index(cls, index_path: Path, glossary_path: Path) -> RagKnowledgeSource:
        return cls(JsonlChunkStore(index_path).all(), glossary_path)

    def search(self, text: str, k: int) -> list[Citation]:
        """Pasajes citables, del más al menos relevante. Vacío si ninguno pasa el umbral."""
        english, translated = self._glossary.explain(text)
        # Las palabras que el glosario ya tradujo no se buscan en español: están en `english`.
        untranslated = {
            term
            for term in terms(text, _QUERY_MIN_LENGTH)
            if term not in _STOPWORDS and term not in translated
        }
        query = untranslated | english
        if not self._chunks or not query:
            return []

        # Una coincidencia aislada no es una respuesta: con varios términos en la pregunta, el
        # fragmento debe coincidir en al menos dos (p. ej. «world» en una lista de acrónimos).
        required = min(MIN_MATCHED_TERMS, len(query))

        scored: list[tuple[float, int]] = []
        for position in range(len(self._chunks)):
            if len(query & self._counts[position].keys()) < required:
                continue
            score = self._score(query, position)
            if score >= MIN_SCORE:
                scored.append((-score, position))
        scored.sort()

        return [self._citation(self._chunks[position], query) for _, position in scored[:k]]

    def _citation(self, chunk: Chunk, query: set[str]) -> Citation:
        return Citation(
            document_code=chunk.document_code,
            requirement_ref=chunk.requirement_ref,
            page=chunk.page,
            excerpt=_snippet(chunk.content, query, self._idf),
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
