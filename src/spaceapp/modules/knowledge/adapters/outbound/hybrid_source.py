"""Hybrid search: words (BM25 + glossary) propose and meaning (embeddings) orders.

Word search almost always finds the passage in its first 50 results, but leaves it at a bad rank
when the question is a paraphrase ('daily energy' versus *energy requirements*). The embeddings
model does understand the paraphrase, but on its own it also answers nearby out-of-scope topics (a
medicine, a price). So they split the work: words decide whether there is an answer and which
passages are candidates; the cosine reorders them, and those that almost tie with the best keep
the word order. Measured on the tuning sets, reordering this way gave more hits in the top 3 than
fusing the two lists with RRF.

If the model does not answer, or there are no vectors, it searches by words only: without Ollama
the assistant keeps working, with the retrieval it had before.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.rag_source import RagKnowledgeSource
from spaceapp.modules.knowledge.domain.model import Citation
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex
from spaceapp.modules.knowledge.ports import Embedder, EmbeddingError, PassageSource

# Below this cosine similarity, a passage does not count as similar to the question.
DEFAULT_MIN_SIMILARITY = 0.5
DEPTH = 50
# Two passages within this distance of the best cosine are a tie: the difference is model noise
# (in tuning, 0.02 raised the first rank from 38% to 50% without lowering the top 3).
NEAR_BEST = 0.02
CACHE_SIZE = 256
DEFAULT_VECTORS_NAME = "embeddings.json"


class HybridKnowledgeSource:
    def __init__(
        self,
        lexical: RagKnowledgeSource,
        vectors: VectorIndex,
        embedder: Embedder,
        *,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        depth: int = DEPTH,
    ) -> None:
        self._lexical = lexical
        self._vectors = vectors
        self._embedder = embedder
        self._min_similarity = min_similarity
        self._depth = depth
        row_of = {chunk_id: row for row, chunk_id in enumerate(vectors.ids)}
        # Vector row of each citable fragment; `None` if it has no vector yet.
        self._row_of_position = [row_of.get(chunk.id) for chunk in lexical.chunks]
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def search(self, text: str, k: int) -> list[Citation]:
        positions, query = self._lexical.rank(text)
        if not positions:  # words find nothing: meaning alone does not decide
            return []
        similarities = self._similarities(text)
        if similarities is None:  # no model: words only
            return [self._lexical.citation(p, query) for p in positions[:k]]

        ordered = self._reorder(positions[: self._depth], similarities)
        if ordered is None:
            return []
        return [self._lexical.citation(position, query) for position in ordered[:k]]

    def _similarities(self, text: str) -> list[float] | None:
        try:
            return self._vectors.similarities(self._query_vector(text))
        except (EmbeddingError, ValueError):  # model down, or vectors from another model
            return None

    def _query_vector(self, text: str) -> list[float]:
        cached = self._cache.get(text)
        if cached is not None:
            self._cache.move_to_end(text)
            return cached
        [vector] = self._embedder.embed([text])
        self._cache[text] = vector
        if len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return vector

    def _reorder(self, candidates: list[int], similarities: list[float]) -> list[int] | None:
        """First those that almost tie with the best cosine (word order); then the rest.

        `None` if none is similar enough. A fragment without a vector cannot be compared: it goes
        last, in word order.
        """
        row_of = self._row_of_position
        scored = [(similarities[row], p) for p in candidates if (row := row_of[p]) is not None]
        without_vector = [p for p in candidates if row_of[p] is None]
        if not scored:
            return without_vector
        best = max(similarity for similarity, _ in scored)
        if best < self._min_similarity:
            return None
        near = [p for similarity, p in scored if similarity >= best - NEAR_BEST]
        rest = sorted(
            ((similarity, p) for similarity, p in scored if similarity < best - NEAR_BEST),
            key=lambda pair: -pair[0],
        )
        return near + [p for _, p in rest] + without_vector


def build_knowledge_source(
    index_path: Path,
    glossary_path: Path,
    embedder: Embedder,
    *,
    vectors_path: Path | None = None,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> PassageSource:
    """Hybrid if there are vectors from the same model; otherwise, words only."""
    lexical = RagKnowledgeSource.from_index(index_path, glossary_path)
    try:
        vectors = VectorIndex.load(vectors_path or index_path.with_name(DEFAULT_VECTORS_NAME))
    except ValueError:  # half-written files: search by words instead of failing
        return lexical
    if vectors is None or vectors.model != embedder.model:
        return lexical
    return HybridKnowledgeSource(lexical, vectors, embedder, min_similarity=min_similarity)
