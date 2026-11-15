"""Search over the NASA PDF fragments, falling back to the demo source.

Without an embeddings model: it scores by terms, weighted by rarity, and translates the question
with a glossary because the documents are in English. If a multilingual model is chosen, this
adapter is the one to replace (plan, decision 5).
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
    stem,
    terms,
    token_counts,
)
from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.ingest.chunking import MAX_CHARS, Chunk, searchable_chunks
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ports import PassageSource

# Below this score there is no passage: a word present in almost every fragment is not enough.
MIN_SCORE = 1.0
MIN_MATCHED_TERMS = 2
BM25_K1 = 1.5
BM25_B = 0.75
# The full fragment is cited: cutting to 500 characters hid the figure in half of the cases
# (measured on the real PDFs: with 500 it showed 7 of 25 answers; with 1200, 13 of 25).
EXCERPT_MAX_CHARS = MAX_CHARS
_QUERY_MIN_LENGTH = 4
# Question words that say nothing about the topic ('how much ... is needed'): if they count as
# terms, the passage would have to contain them and the figure being looked for would fall out of
# the results.
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
        "much",
        "many",
        "does",
        "should",
        "would",
        "could",
        "about",
        "there",
        "when",
        "where",
        "whom",
        "whose",
        "need",
        "needs",
        "needed",
        "required",
        "each",
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
        "cuantos",
        "cuantas",
        "quien",
        "necesita",
        "necesito",
        "necesitan",
        "debe",
        "deben",
        "puede",
        "pueden",
        "tiene",
        "tienen",
    ]
)


def load_glossary(path: Path) -> Glossary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Glossary([(entry["es"], entry["en"]) for entry in raw["entries"]])


_WORD = re.compile(r"[a-z0-9]+")
_CONTEXT_BEFORE = 120


def _snippet(content: str, query: set[str], idf: dict[str, float]) -> str:
    """Excerpt of up to 500 characters: the part of the passage that best covers the question.

    Always cutting the beginning would hide the figure when it is at the end of a long fragment.
    Each term counts by its rarity: a rare term ('diluent') weighs more than two common ones
    ('cabin', 'pressure'), which appear everywhere and do not point to where the answer is.
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

    width = EXCERPT_MAX_CHARS - 2  # room left for the ellipses
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
        # Loose titles and index entries are not citable passages: they are discarded.
        self._chunks = searchable_chunks(chunks)
        self._counts = [token_counts(chunk.content) for chunk in self._chunks]
        self._lengths = [sum(counts.values()) for counts in self._counts]
        self._average_length = (sum(self._lengths) / len(self._lengths)) if self._lengths else 1.0
        document_frequency = Counter(term for counts in self._counts for term in counts)
        total = len(self._chunks)
        self._idf = {
            term: math.log(1 + (total + 1) / count) for term, count in document_frequency.items()
        }

    def _score(self, query: set[str], position: int) -> float:
        """BM25: weighs each term by its rarity, its frequency and the length of the fragment."""
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

    @property
    def chunks(self) -> list[Chunk]:
        """The citable fragments, in the order of the positions that `rank` returns."""
        return self._chunks

    def search(self, text: str, k: int) -> list[Citation]:
        """Citable passages, from most to least relevant. Empty if none passes the threshold."""
        positions, query = self.rank(text)
        return [self.citation(position, query) for position in positions[:k]]

    def rank(self, text: str) -> tuple[list[int], set[str]]:
        """Positions of the fragments that pass the thresholds, from most to least relevant.

        It also returns the query terms, which `citation` uses to pick the excerpt.
        """
        english, translated = self._glossary.explain(text)
        # Words the glossary already translated are not searched in Spanish: they are in `english`.
        untranslated = {
            term
            for term in terms(text, _QUERY_MIN_LENGTH)
            if term not in _STOPWORDS and term not in translated
        }
        query = untranslated | english
        if not self._chunks or not query:
            return [], set()

        # A lone match is not an answer: with several terms in the question, the
        # fragment must match at least two (e.g. 'world' in a list of acronyms).
        required = min(MIN_MATCHED_TERMS, len(query))

        scored: list[tuple[float, int]] = []
        for position in range(len(self._chunks)):
            if len(query & self._counts[position].keys()) < required:
                continue
            score = self._score(query, position)
            if score >= MIN_SCORE:
                scored.append((-score, position))
        scored.sort()

        return [position for _, position in scored], query

    def citation(self, position: int, query: set[str]) -> Citation:
        chunk = self._chunks[position]
        return Citation(
            document_code=chunk.document_code,
            requirement_ref=chunk.requirement_ref,
            page=chunk.page,
            excerpt=_snippet(chunk.content, query, self._idf),
            evidence_state=EvidenceState(chunk.evidence_state),
        )


class FallbackKnowledgeSource:
    """`jurado` (judge) profile: RAG first; if a passage is missing, use the demo source."""

    def __init__(self, primary: PassageSource, fallback: PassageSource) -> None:
        self._primary = primary
        self._fallback = fallback

    def search(self, text: str, k: int) -> list[Citation]:
        found = self._primary.search(text, k)
        return found if found else self._fallback.search(text, k)
