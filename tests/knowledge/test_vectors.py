from __future__ import annotations

from pathlib import Path

import pytest

from spaceapp.modules.knowledge.ingest.vectors import VectorIndex


def test_the_similarity_is_the_cosine_so_the_length_of_a_vector_does_not_matter() -> None:
    index = VectorIndex.build("m", ["a", "b"], [[3.0, 4.0], [0.0, 5.0]])

    similarities = index.similarities([6.0, 8.0])

    assert similarities[0] == pytest.approx(1.0)
    assert similarities[1] == pytest.approx(0.8)


def test_a_zero_query_or_a_zero_vector_gives_zero_instead_of_failing() -> None:
    index = VectorIndex.build("m", ["a", "zero"], [[1.0, 0.0], [0.0, 0.0]])

    assert index.similarities([0.0, 0.0]) == [0.0, 0.0]
    assert index.similarities([1.0, 0.0]) == [pytest.approx(1.0), 0.0]


def test_the_vectors_survive_a_round_trip_through_the_files(tmp_path: Path) -> None:
    path = tmp_path / "index" / "embeddings.json"
    VectorIndex.build("bge-m3", ["a", "b"], [[1.0, 2.0, 3.0], [-1.0, 0.5, 0.0]]).save(path)

    loaded = VectorIndex.load(path)

    assert loaded is not None
    assert loaded.model == "bge-m3"
    assert loaded.dim == 3
    assert loaded.ids == ["a", "b"]
    assert loaded.similarities([1.0, 2.0, 3.0])[0] == pytest.approx(1.0, abs=1e-6)


def test_load_returns_nothing_when_there_are_no_vectors_yet(tmp_path: Path) -> None:
    assert VectorIndex.load(tmp_path / "embeddings.json") is None


def test_load_rejects_vectors_that_do_not_match_the_list_of_ids(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.json"
    VectorIndex.build("m", ["a", "b"], [[1.0, 0.0], [0.0, 1.0]]).save(path)
    path.with_suffix(".f32").write_bytes(b"\x00" * 4)  # un solo número, no 2 por 2

    with pytest.raises(ValueError, match="no coincide"):
        VectorIndex.load(path)


def test_a_vector_can_be_looked_up_by_id() -> None:
    index = VectorIndex.build("m", ["a", "b"], [[3.0, 4.0], [0.0, 2.0]])

    assert index.vector("a") == [pytest.approx(0.6), pytest.approx(0.8)]
    assert index.vector("missing") is None
    assert "b" in index
    assert len(index) == 2


def test_vectors_of_different_lengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="dimensi"):
        VectorIndex.build("m", ["a", "b"], [[1.0, 0.0], [1.0]])


def test_an_empty_index_has_no_similarities() -> None:
    assert VectorIndex.build("m", [], []).similarities([1.0]) == []


def test_saving_leaves_no_temporary_files_behind(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.json"

    VectorIndex.build("m", ["a"], [[1.0, 0.0]]).save(path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["embeddings.f32", "embeddings.json"]
