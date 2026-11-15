"""Vectors command: `python -m spaceapp.modules.knowledge.ingest.embed`.

Computes with Ollama the vector of each citable fragment and stores it next to the index. It is
kept apart from the ingestion on purpose: the ingestion needs no network or model, and the search
keeps working by words if the vectors do not exist. It is incremental: it only computes the
fragments that have no vector from the same model.
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
    """Vectors of the citable fragments: (index, computed now, reused)."""
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
        description="Computes the fragment vectors with a local embeddings model."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--url", default=DEFAULT_URL, help="Ollama address")
    parser.add_argument("--batch", type=int, default=32, help="texts per request")
    args = parser.parse_args(argv)

    chunks = JsonlChunkStore(args.index).all() if args.index.exists() else []
    if not chunks:
        print(
            "There is no index. Run the ingestion first: "
            "python -m spaceapp.modules.knowledge.ingest",
            file=sys.stderr,
        )
        return 2

    embedder = embedder or OllamaEmbedder(
        model=args.model, base_url=args.url, batch_size=args.batch
    )
    try:
        existing = VectorIndex.load(args.out)
    except ValueError as error:  # half-written files: everything is recomputed instead of failing
        print(f"Ignoring the previous vectors: {error}", file=sys.stderr)
        existing = None

    def report(done: int, total: int) -> None:
        print(f"  {done}/{total}", flush=True)

    try:
        index, new, reused = build_embeddings(chunks, embedder, existing, progress=report)
    except EmbeddingError as error:
        print(
            f"The vectors could not be computed: {error}\n"
            f"Is Ollama running and the model installed? "
            f"docker exec spaceapp-ollama ollama pull {embedder.model}",
            file=sys.stderr,
        )
        return 1

    index.save(args.out)
    print(
        f"Vectors: {new} new, {reused} reused "
        f"({embedder.model}, {index.dim} dimensions) in {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
