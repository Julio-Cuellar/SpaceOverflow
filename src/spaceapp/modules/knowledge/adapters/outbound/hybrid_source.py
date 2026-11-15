"""Búsqueda híbrida: por palabras (BM25 + glosario) y por significado (embeddings), fusionadas.

La búsqueda por palabras no entiende paráfrasis («energía diaria» frente a *energy requirements*) ni
cifras en tablas; la de significado sí, pero necesita el modelo. Cada canal ordena los fragmentos y
las dos listas se fusionan con RRF (reciprocal rank fusion), que no necesita pesos ajustados a
mano: un pasaje que sale en ambas listas sube, y uno que sale en una sola no desaparece.

Si el modelo no responde, o no hay vectores, se busca solo por palabras: sin Ollama el asistente
sigue funcionando, con la recuperación de antes.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.rag_source import RagKnowledgeSource
from spaceapp.modules.knowledge.domain.model import Citation
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex
from spaceapp.modules.knowledge.ports import Embedder, EmbeddingError, PassageSource

# Por debajo de esta similitud coseno, un pasaje no cuenta como parecido a la pregunta.
DEFAULT_MIN_SIMILARITY = 0.5
RRF_K = 60
DEPTH = 50
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
        rrf_k: int = RRF_K,
        require_word_match: bool = True,
    ) -> None:
        self._lexical = lexical
        self._vectors = vectors
        self._embedder = embedder
        self._min_similarity = min_similarity
        self._depth = depth
        self._rrf_k = rrf_k
        # El significado reordena y completa lo que encontraron las palabras, pero no decide solo
        # que una pregunta tiene respuesta: un tema cercano y fuera de alcance (una medicina, un
        # precio) se parece a los pasajes médicos sin que ninguno lo conteste.
        self._require_word_match = require_word_match
        row_of = {chunk_id: row for row, chunk_id in enumerate(vectors.ids)}
        # Fila de vectores de cada fragmento citable; `None` si todavía no tiene vector.
        self._row_of_position = [row_of.get(chunk.id) for chunk in lexical.chunks]
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def search(self, text: str, k: int) -> list[Citation]:
        positions, query = self._lexical.rank(text)
        if self._require_word_match and not positions:
            return []
        similarities = self._similarities(text)
        if similarities is None:  # sin modelo: solo palabras
            return [self._lexical.citation(p, query) for p in positions[:k]]

        by_meaning = self._rank_by_meaning(similarities)
        fused = self._fuse(positions[: self._depth], by_meaning)
        return [self._lexical.citation(position, query) for position in fused[:k]]

    def _similarities(self, text: str) -> list[float] | None:
        try:
            return self._vectors.similarities(self._query_vector(text))
        except (EmbeddingError, ValueError):  # modelo caído, o vectores de otro modelo
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

    def _rank_by_meaning(self, similarities: list[float]) -> list[int]:
        scored = [
            (similarities[row], position)
            for position, row in enumerate(self._row_of_position)
            if row is not None and similarities[row] >= self._min_similarity
        ]
        scored.sort(key=lambda pair: -pair[0])
        return [position for _, position in scored[: self._depth]]

    def _fuse(self, by_words: list[int], by_meaning: list[int]) -> list[int]:
        scores: dict[int, float] = {}
        for ranking in (by_words, by_meaning):
            for rank, position in enumerate(ranking, start=1):
                scores[position] = scores.get(position, 0.0) + 1.0 / (self._rrf_k + rank)
        word_rank = {position: rank for rank, position in enumerate(by_words)}
        return sorted(scores, key=lambda p: (-scores[p], word_rank.get(p, len(word_rank)), p))


def build_knowledge_source(
    index_path: Path,
    glossary_path: Path,
    embedder: Embedder,
    *,
    vectors_path: Path | None = None,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> PassageSource:
    """Híbrida si hay vectores del mismo modelo; si no, solo por palabras."""
    lexical = RagKnowledgeSource.from_index(index_path, glossary_path)
    try:
        vectors = VectorIndex.load(vectors_path or index_path.with_name(DEFAULT_VECTORS_NAME))
    except ValueError:  # archivos a medias: se busca por palabras en vez de fallar
        return lexical
    if vectors is None or vectors.model != embedder.model:
        return lexical
    return HybridKnowledgeSource(lexical, vectors, embedder, min_similarity=min_similarity)
