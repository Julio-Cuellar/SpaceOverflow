"""Fragment vectors: store them, load them and search by cosine similarity (no libraries).

They go in two files together: `embeddings.json` (model, dimension and ids, in row order) and
`embeddings.f32` (the numbers as little-endian float32). They are stored already normalized: this
way the dot product of two vectors is their cosine, and comparing a query with ~2,000 fragments
takes a few tenths of a second in pure Python.
"""

from __future__ import annotations

import json
import math
import sys
from array import array
from collections.abc import Sequence
from operator import mul
from pathlib import Path


def _normalise(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else [0.0] * len(vector)


def _binary_path(meta_path: Path) -> Path:
    return meta_path.with_suffix(".f32")


class VectorIndex:
    def __init__(self, model: str, dim: int, ids: list[str], data: array[float]) -> None:
        self.model = model
        self.dim = dim
        self.ids = ids
        self._data = data
        self._row_of = {chunk_id: row for row, chunk_id in enumerate(ids)}

    @classmethod
    def build(
        cls, model: str, ids: Sequence[str], vectors: Sequence[Sequence[float]]
    ) -> VectorIndex:
        if len(ids) != len(vectors):
            raise ValueError("there is a different number of ids and vectors")
        dim = len(vectors[0]) if vectors else 0
        if any(len(vector) != dim for vector in vectors):
            raise ValueError("the vectors have different dimensions")
        data: array[float] = array("f")
        for vector in vectors:
            data.extend(_normalise(vector))
        return cls(model, dim, list(ids), data)

    def __len__(self) -> int:
        return len(self.ids)

    def __contains__(self, chunk_id: object) -> bool:
        return chunk_id in self._row_of

    def vector(self, chunk_id: str) -> list[float] | None:
        row = self._row_of.get(chunk_id)
        if row is None:
            return None
        return list(self._data[row * self.dim : (row + 1) * self.dim])

    def similarities(self, query: Sequence[float]) -> list[float]:
        """Cosine between the query and each fragment, in the order of `ids`."""
        if not self.ids:
            return []
        if len(query) != self.dim:
            raise ValueError(f"the query has {len(query)} dimensions and the vectors {self.dim}")
        unit = _normalise(query)
        return [
            sum(map(mul, unit, self._data[row * self.dim : (row + 1) * self.dim]))
            for row in range(len(self.ids))
        ]

    def save(self, path: Path) -> None:
        """Writes the numbers first and the json last: if something fails, the old json rules."""
        path.parent.mkdir(parents=True, exist_ok=True)
        binary = _binary_path(path)
        temporary_binary = binary.with_name(binary.name + ".tmp")
        temporary_meta = path.with_name(path.name + ".tmp")

        data = array("f", self._data)
        if sys.byteorder == "big":
            data.byteswap()
        temporary_binary.write_bytes(data.tobytes())
        meta = {"model": self.model, "dim": self.dim, "ids": self.ids}
        temporary_meta.write_text(json.dumps(meta), encoding="utf-8")
        temporary_binary.replace(binary)
        temporary_meta.replace(path)

    @classmethod
    def load(cls, path: Path) -> VectorIndex | None:
        """The stored vectors, or `None` if they have not been computed yet."""
        binary = _binary_path(path)
        if not path.exists() or not binary.exists():
            return None
        meta = json.loads(path.read_text(encoding="utf-8"))
        ids: list[str] = meta["ids"]
        dim = int(meta["dim"])
        raw = binary.read_bytes()
        data: array[float] = array("f")
        if len(raw) % data.itemsize != 0 or len(raw) // data.itemsize != len(ids) * dim:
            raise ValueError(
                f"{binary.name} does not match {path.name}: "
                f"{len(raw)} bytes for {len(ids)} vectors of {dim} numbers"
            )
        data.frombytes(raw)
        if sys.byteorder == "big":
            data.byteswap()
        return cls(str(meta["model"]), dim, ids, data)
