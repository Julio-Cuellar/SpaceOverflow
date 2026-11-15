"""Comando de vectores: `python -m spaceapp.modules.knowledge.ingest.embed`.

Calcula con Ollama el vector de cada fragmento citable y lo guarda junto al índice. Va aparte de la
ingesta a propósito: la ingesta no necesita red ni modelo, y la búsqueda sigue funcionando por
palabras si los vectores no existen. Es incremental: solo calcula los fragmentos que no tienen
vector del mismo modelo.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.ollama_embedder import (
    DEFAULT_MODEL,
    DEFAULT_URL,
    OllamaEmbedder,
)
from spaceapp.modules.knowledge.ingest.chunking import Chunk, searchable_chunks
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex
from spaceapp.modules.knowledge.ports import Embedder, EmbeddingError

DEFAULT_INDEX = Path("data/knowledge/index/chunks.jsonl")
DEFAULT_OUT = Path("data/knowledge/index/embeddings.json")
PROGRESS_BATCH = 64


def build_embeddings(
    chunks: Sequence[Chunk],
    embedder: Embedder,
    existing: VectorIndex | None = None,
    progress: Callable[[int, int], None] | None = None,
    batch: int = PROGRESS_BATCH,
) -> tuple[VectorIndex, int, int]:
    """Vectores de los fragmentos citables: (índice, calculados ahora, reutilizados)."""
    searchable = searchable_chunks(chunks)
    reusable = existing if existing is not None and existing.model == embedder.model else None

    vectors: dict[str, list[float]] = {}
    pending: list[Chunk] = []
    for chunk in searchable:
        vector = reusable.vector(chunk.id) if reusable is not None else None
        if vector is None:
            pending.append(chunk)
        else:
            vectors[chunk.id] = vector
    reused = len(vectors)

    for start in range(0, len(pending), batch):
        part = pending[start : start + batch]
        for chunk, vector in zip(part, embedder.embed([c.content for c in part]), strict=True):
            vectors[chunk.id] = vector
        if progress is not None:
            progress(min(start + batch, len(pending)), len(pending))

    ids = [chunk.id for chunk in searchable]
    index = VectorIndex.build(embedder.model, ids, [vectors[chunk_id] for chunk_id in ids])
    return index, len(pending), reused


def main(argv: Sequence[str] | None = None, embedder: Embedder | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calcula los vectores de los fragmentos con un modelo de embeddings local."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--url", default=DEFAULT_URL, help="dirección de Ollama")
    parser.add_argument("--batch", type=int, default=32, help="textos por petición")
    args = parser.parse_args(argv)

    chunks = JsonlChunkStore(args.index).all() if args.index.exists() else []
    if not chunks:
        print(
            "No hay índice. Ejecuta primero la ingesta: "
            "python -m spaceapp.modules.knowledge.ingest",
            file=sys.stderr,
        )
        return 2

    embedder = embedder or OllamaEmbedder(
        model=args.model, base_url=args.url, batch_size=args.batch
    )
    try:
        existing = VectorIndex.load(args.out)
    except ValueError as error:  # archivos a medias: se recalcula todo en vez de fallar
        print(f"Se ignoran los vectores anteriores: {error}", file=sys.stderr)
        existing = None

    def report(done: int, total: int) -> None:
        print(f"  {done}/{total}", flush=True)

    try:
        index, new, reused = build_embeddings(chunks, embedder, existing, progress=report)
    except EmbeddingError as error:
        print(
            f"No se pudieron calcular los vectores: {error}\n"
            f"¿Está Ollama en marcha y el modelo instalado? "
            f"docker exec spaceapp-ollama ollama pull {embedder.model}",
            file=sys.stderr,
        )
        return 1

    index.save(args.out)
    print(
        f"Vectores: {new} nuevos, {reused} reutilizados "
        f"({embedder.model}, {index.dim} dimensiones) en {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
