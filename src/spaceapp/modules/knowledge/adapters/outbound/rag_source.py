"""Search over the NASA PDF chunks, falling back to the demo source.

No embeddings model: it scores by terms, weighted by their rarity. Questions and documents are
both in English, so no translation is needed. If an embeddings model is chosen later, this
adapter is the one that gets replaced (architecture plan, decision 5).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.domain.model import Citation, EvidenceState
from spaceapp.modules.knowledge.domain.terms import stem, terms, token_counts
from spaceapp.modules.knowledge.ingest.chunking import MAX_CHARS, Chunk, searchable_chunks
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ports import PassageSource

# Below this score there is no passage: a word present in almost every chunk is not enough.
MIN_SCORE = 1.0
MIN_MATCHED_TERMS = 2
BM25_K1 = 1.5
BM25_B = 0.75
# The whole chunk is cited: trimming to 500 characters hid the figure in half of the cases
# (measured on the real PDFs: with 500 the figure showed in 7 of 25 answers; with 1200, in 13).
EXCERPT_MAX_CHARS = MAX_CHARS
_QUERY_MIN_LENGTH = 3
# Question words that say nothing about the topic. They are stemmed like the query terms.
_STOPWORDS = frozenset(
    stem(word)
    for word in (
        "the",
        "and",
        "for",
        "are",
        "was",
        "were",
        "not",
        "but",
        "you",
        "your",
        "our",
        "can",
        "does",
        "did",
        "has",
        "have",
        "had",
        "its",
        "per",
        "may",
        "how",
        "why",
        "who",
        "whom",
        "whose",
        "what",
        "when",
        "where",
        "which",
        "that",
        "this",
        "these",
        "those",
        "with",
        "from",
        "into",
        "about",
        "shall",
        "will",
        "would",
        "should",
        "could",
        "than",
        "then",
        "there",
        "their",
        "they",
        "them",
        "much",
        "many",
        "some",
        "any",
        "all",
        "need",
        "needs",
        "needed",
        "required",
        "require",
        "must",
        "also",
        "only",
        "each",
        "other",
        "such",
        "been",
        "being",
        "very",
    )
)

_WORD = re.compile(r"[a-z0-9]+")
_CONTEXT_BEFORE = 120


def _snippet(content: str, query: set[str], idf: dict[str, float]) -> str:
    """Excerpt of at most `EXCERPT_MAX_CHARS`: the part of the passage that best fits the question.

    Always cutting the beginning would hide the figure when it is at the end of a long chunk.
    Each term counts by its rarity: a rare term ("diluent") weighs more than two common ones
    ("cabin", "pressure"), which appear everywhere and do not point to where the answer is.
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

    width = EXCERPT_MAX_CHARS - 2  # leaves room for the ellipses
    if start > 0:
        space = content.find(" ", start)
        if 0 <= space < start + 40:
            start = space + 1  # do not start mid-word
    piece = content[start : start + width]
    truncated = start + width < len(content)
    if truncated:
        cut = piece.rfind(" ")
        if cut > width // 2:
            piece = piece[:cut]
    return ("…" if start > 0 else "") + piece.strip() + ("…" if truncated else "")


class RagKnowledgeSource:
    def __init__(self, chunks: Sequence[Chunk]) -> None:
        # Stray titles and index entries are not citable passages: they are discarded.
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
        """BM25: weighs each term by its rarity, its frequency and the length of the chunk."""
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
    def from_index(cls, index_path: Path) -> RagKnowledgeSource:
        return cls(JsonlChunkStore(index_path).all())

    @property
    def chunks(self) -> list[Chunk]:
        """The citable chunks, in the order of the positions that `rank` returns."""
        return self._chunks

    def search(self, text: str, k: int) -> list[Citation]:
        """Citable passages, from most to least relevant. Empty if none passes the threshold."""
        positions, query = self.rank(text)
        return [self.citation(position, query) for position in positions[:k]]

    def rank(self, text: str) -> tuple[list[int], set[str]]:
        """Positions of the chunks that pass the thresholds, from most to least relevant.

        It also returns the query terms, which `citation` uses to pick the excerpt.
        """
        query = {term for term in terms(text, _QUERY_MIN_LENGTH) if term not in _STOPWORDS}
        if not self._chunks or not query:
            return [], set()

        # An isolated match is not an answer: with several terms in the question, the chunk
        # must match at least two (e.g. "world" in a list of acronyms).
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
    """Profile `jury`: RAG first; if no passage is found, falls back to the demo source."""

    def __init__(self, primary: PassageSource, fallback: PassageSource) -> None:
        self._primary = primary
        self._fallback = fallback

    def search(self, text: str, k: int) -> list[Citation]:
        found = self._primary.search(text, k)
        return found if found else self._fallback.search(text, k)
