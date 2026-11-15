"""Búsqueda híbrida: las palabras (BM25 + glosario) proponen y el significado (embeddings) ordena.

La búsqueda por palabras acierta con el pasaje en sus primeros 50 resultados casi siempre, pero lo
deja en un puesto malo cuando la pregunta es una paráfrasis («energía diaria» frente a *energy
requirements*). El modelo de embeddings sí entiende la paráfrasis, pero por sí solo responde también
temas cercanos fuera de alcance (una medicina, un precio). Por eso reparten el trabajo: las palabras
deciden si hay respuesta y qué pasajes son candidatos; el coseno los reordena, y los que casi
empatan con el mejor conservan el orden de las palabras. Medido sobre los
conjuntos de ajuste, reordenar así dio más aciertos en el top 3 que fusionar las dos listas con RRF.

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
DEPTH = 50
# Dos pasajes a menos de esta distancia del mejor coseno son un empate: la diferencia es ruido del
# modelo (en el ajuste, 0,02 subió el primer puesto de 38 % a 50 % sin bajar el top 3).
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
        # Fila de vectores de cada fragmento citable; `None` si todavía no tiene vector.
        self._row_of_position = [row_of.get(chunk.id) for chunk in lexical.chunks]
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def search(self, text: str, k: int) -> list[Citation]:
        positions, query = self._lexical.rank(text)
        if not positions:  # las palabras no encuentran nada: el significado no decide solo
            return []
        similarities = self._similarities(text)
        if similarities is None:  # sin modelo: solo palabras
            return [self._lexical.citation(p, query) for p in positions[:k]]

        ordered = self._reorder(positions[: self._depth], similarities)
        if ordered is None:
            return []
        return [self._lexical.citation(position, query) for position in ordered[:k]]

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

    def _reorder(self, candidates: list[int], similarities: list[float]) -> list[int] | None:
        """Primero los casi empatados con el mejor coseno (orden de las palabras); luego el resto.

        `None` si ninguno se parece lo bastante. Un fragmento sin vector no se puede comparar: va
        al final, en el orden de las palabras.
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
    """Híbrida si hay vectores del mismo modelo; si no, solo por palabras."""
    lexical = RagKnowledgeSource.from_index(index_path, glossary_path)
    try:
        vectors = VectorIndex.load(vectors_path or index_path.with_name(DEFAULT_VECTORS_NAME))
    except ValueError:  # archivos a medias: se busca por palabras en vez de fallar
        return lexical
    if vectors is None or vectors.model != embedder.model:
        return lexical
    return HybridKnowledgeSource(lexical, vectors, embedder, min_similarity=min_similarity)
