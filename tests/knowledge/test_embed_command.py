from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.ingest.chunking import Chunk, chunk_page, searchable_chunks
from spaceapp.modules.knowledge.ingest.embed import build_embeddings, main
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex

LONG = "The crew shall keep the average carbon dioxide level below the stated limit at all times."


class FakeEmbedder:
    def __init__(self, model: str = "fake") -> None:
        self.model = model
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


def chunks() -> list[Chunk]:
    return [
        *chunk_page("DOC", 1, LONG, "TB"),
        *chunk_page("DOC", 2, LONG.replace("carbon dioxide", "oxygen"), "TB"),
        *chunk_page("DOC", 3, "1.2 Scope", "TB"),  # a title: not a citable passage
    ]


def test_only_passages_that_can_be_cited_are_kept_as_searchable() -> None:
    assert [c.page for c in searchable_chunks(chunks())] == [1, 2]


def test_embeds_only_the_citable_passages() -> None:
    embedder = FakeEmbedder()

    index, new, reused = build_embeddings(chunks(), embedder)

    assert len(index) == 2
    assert (new, reused) == (2, 0)
    assert sum(len(call) for call in embedder.calls) == 2


def test_a_second_run_reuses_the_vectors_it_already_has() -> None:
    first = build_embeddings(chunks(), FakeEmbedder())[0]
    embedder = FakeEmbedder()

    index, new, reused = build_embeddings(chunks(), embedder, existing=first)

    assert (new, reused) == (0, 2)
    assert embedder.calls == []
    assert index.ids == first.ids


def test_it_only_embeds_the_passages_that_are_new() -> None:
    first = build_embeddings(chunks()[:1], FakeEmbedder())[0]
    embedder = FakeEmbedder()

    index, new, reused = build_embeddings(chunks(), embedder, existing=first)

    assert (new, reused) == (1, 1)
    assert len(index) == 2


def test_vectors_of_passages_that_left_the_index_are_dropped() -> None:
    first = build_embeddings(chunks(), FakeEmbedder())[0]

    index, _, _ = build_embeddings(chunks()[:1], FakeEmbedder(), existing=first)

    assert index.ids == [chunks()[0].id]


def test_vectors_made_by_another_model_are_not_reused() -> None:
    first = build_embeddings(chunks(), FakeEmbedder("old"))[0]
    embedder = FakeEmbedder("new")

    index, new, reused = build_embeddings(chunks(), embedder, existing=first)

    assert (new, reused) == (2, 0)
    assert index.model == "new"


class TestCommand:
    def prepare(self, tmp_path: Path) -> tuple[Path, Path]:
        index = tmp_path / "chunks.jsonl"
        JsonlChunkStore(index).add(chunks())
        return index, tmp_path / "embeddings.json"

    def test_writes_the_vectors_next_to_the_index(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index, out = self.prepare(tmp_path)

        code = main(["--index", str(index), "--out", str(out)], embedder=FakeEmbedder())

        loaded = VectorIndex.load(out)
        assert code == 0
        assert loaded is not None and len(loaded) == 2
        assert "2 new, 0 reused" in capsys.readouterr().out

    def test_running_it_again_does_not_call_the_model(self, tmp_path: Path) -> None:
        index, out = self.prepare(tmp_path)
        main(["--index", str(index), "--out", str(out)], embedder=FakeEmbedder())
        embedder = FakeEmbedder()

        code = main(["--index", str(index), "--out", str(out)], embedder=embedder)

        assert code == 0
        assert embedder.calls == []

    def test_fails_clearly_when_there_is_no_index_yet(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            ["--index", str(tmp_path / "no-existe.jsonl"), "--out", str(tmp_path / "e.json")],
            embedder=FakeEmbedder(),
        )

        assert code == 2
        assert "ingestion" in capsys.readouterr().err

    def test_says_how_to_install_the_model_when_ollama_cannot_be_reached(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index, out = self.prepare(tmp_path)

        code = main(["--index", str(index), "--out", str(out), "--url", "http://127.0.0.1:9"])

        assert code == 1
        assert "ollama pull bge-m3" in capsys.readouterr().err
        assert not out.exists()
