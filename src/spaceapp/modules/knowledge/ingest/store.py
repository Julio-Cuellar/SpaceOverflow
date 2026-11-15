"""Chunk store. In memory for tests and in a JSONL file for local ingestion.

Once PostgreSQL exists (dev A, I1), the `knowledge` schema (`document`, `chunk`) replaces the
file: this port is the point of change.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from spaceapp.modules.knowledge.ingest.chunking import Chunk


class ChunkStore(Protocol):
    def add(self, chunks: list[Chunk]) -> int:
        """Stores the new chunks and returns how many were new (idempotent ingestion)."""
        ...

    def all(self) -> list[Chunk]: ...


class InMemoryChunkStore:
    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}

    def add(self, chunks: list[Chunk]) -> int:
        new = [chunk for chunk in chunks if chunk.id not in self._chunks]
        for chunk in new:
            self._chunks[chunk.id] = chunk
        return len(new)

    def all(self) -> list[Chunk]:
        return list(self._chunks.values())


class JsonlChunkStore(InMemoryChunkStore):
    """Same as the in-memory one, but keeps the chunks in a file between runs."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    chunk = Chunk(**json.loads(line))
                    self._chunks[chunk.id] = chunk

    def add(self, chunks: list[Chunk]) -> int:
        before = set(self._chunks)
        added = super().add(chunks)
        if added:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                for chunk in chunks:
                    if chunk.id not in before:
                        handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
                        before.add(chunk.id)
        return added
