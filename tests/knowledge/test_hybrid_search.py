from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.hybrid_source import (
    HybridKnowledgeSource,
    build_knowledge_source,
)
from spaceapp.modules.knowledge.adapters.outbound.rag_source import RagKnowledgeSource
from spaceapp.modules.knowledge.ingest.chunking import Chunk, chunk_page
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex
from spaceapp.modules.knowledge.ports import EmbeddingError

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY = ROOT / "data" / "knowledge" / "glossary_es_en.json"
STANDARD = "NASA-STD-3001 Vol. 2 Rev F"
BRIEF = "OCHMO-TB-004 CO₂"

CO2_LIMIT = chunk_page(
    STANDARD,
    5,
    "[V2 6004] The ppCO2 average over 1 hour shall be less than or equal to 3 mmHg.",
    "VERIFICADO",
)
HEADACHE = chunk_page(
    BRIEF,
    2,
    "Headache can occur between 2.8 and 4.5 mmHg of ppCO2. Fatigue, poor sleep and nausea appear.",
    "TB",
)
NOISE = chunk_page(
    STANDARD,
    9,
    "[V2 6079] Crew quarters noise limit is NC-40 in missions longer than 30 days.",
    "VERIFICADO",
)
CHUNKS: list[Chunk] = [*CO2_LIMIT, *HEADACHE, *NOISE]
NOISE_REF = "V2 6079"


def axis(position: int) -> list[float]:
    vector = [0.0, 0.0, 0.0]
    vector[position] = 1.0
    return vector


def vectors(include: Sequence[Chunk] = tuple(CHUNKS), model: str = "fake") -> VectorIndex:
    return VectorIndex.build(
        model, [c.id for c in include], [axis(CHUNKS.index(c)) for c in include]
    )


class FakeEmbedder:
    """Cada pregunta conocida se parece a un pasaje; las desconocidas, a ninguno."""

    def __init__(self, answers: dict[str, list[float]], model: str = "fake") -> None:
        self.model = model
        self._answers = answers
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._answers.get(text, [0.0, 0.0, 0.0]) for text in texts]


class BrokenEmbedder:
    model = "fake"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingError("Ollama no responde")


def hybrid(
    answers: dict[str, list[float]], *, min_similarity: float = 0.5, **kwargs: object
) -> tuple[HybridKnowledgeSource, FakeEmbedder]:
    embedder = FakeEmbedder(answers)
    source = HybridKnowledgeSource(
        RagKnowledgeSource(CHUNKS, GLOSSARY),
        vectors(),
        embedder,
        min_similarity=min_similarity,
        **kwargs,  # type: ignore[arg-type]
    )
    return source, embedder


def test_meaning_alone_never_answers_a_question_the_words_did_not_find() -> None:
    # Un tema cercano pero fuera de alcance (una medicina, un precio) se parece a los pasajes
    # médicos por significado: sin una sola palabra en común no hay base para citarlos.
    question = "What makes my skull throb?"
    assert RagKnowledgeSource(CHUNKS, GLOSSARY).search(question, k=3) == []
    source, _ = hybrid({question: [0.1, 0.99, 0.0]})

    assert source.search(question, k=3) == []


def test_meaning_reorders_the_passages_the_words_found() -> None:
    question = "ppCO2 mmHg"
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY).search(question, k=3)
    assert {r.document_code for r in lexical} == {STANDARD, BRIEF}
    # Por significado, el pasaje del dolor de cabeza se parece más a la pregunta.
    source, _ = hybrid({question: [0.4, 0.9, 0.0]})

    results = source.search(question, k=3)

    assert results[0].document_code == BRIEF
    assert {r.document_code for r in results} == {STANDARD, BRIEF}


def test_meaning_decides_the_order_even_when_the_words_prefer_another_passage() -> None:
    question = "ppCO2 mmHg"
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY).search(question, k=3)
    assert lexical[0].requirement_ref == "V2 6004"
    source, _ = hybrid({question: [0.5, 0.9, 0.0]})

    assert source.search(question, k=3)[0].document_code == BRIEF


def test_passages_almost_as_close_in_meaning_as_the_best_keep_the_order_of_the_words() -> None:
    question = "ppCO2 mmHg"
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY).search(question, k=3)
    assert lexical[0].document_code == STANDARD
    # El pasaje del dolor de cabeza se parece un poco más (0,714 frente a 0,700), pero la
    # diferencia es ruido del modelo: manda el orden de las palabras.
    source, _ = hybrid({question: [1.0, 1.02, 0.0]})

    assert source.search(question, k=3)[0].document_code == STANDARD


def test_a_passage_the_words_did_not_find_is_not_added_by_meaning() -> None:
    question = "ppCO2 mmHg"
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY).search(question, k=3)
    assert NOISE_REF not in [r.requirement_ref for r in lexical]
    source, _ = hybrid({question: [0.0, 0.1, 0.99]})

    assert NOISE_REF not in [r.requirement_ref for r in source.search(question, k=3)]


def test_nothing_is_cited_when_no_passage_is_close_in_meaning() -> None:
    question = "ppCO2 mmHg"
    source, _ = hybrid({question: [0.1, 0.1, 0.1]}, min_similarity=0.9)

    assert source.search(question, k=3) == []


def test_returns_at_most_k_passages() -> None:
    question = "ppCO2 mmHg"
    source, _ = hybrid({question: [1.0, 1.0, 1.0]}, min_similarity=0.1)

    assert len(source.search(question, k=1)) == 1


def test_falls_back_to_the_lexical_search_when_the_model_cannot_be_reached() -> None:
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY)
    source = HybridKnowledgeSource(lexical, vectors(), BrokenEmbedder(), min_similarity=0.5)
    question = "What is the one-hour average CO2 limit?"

    assert source.search(question, k=3) == lexical.search(question, k=3)


def test_the_same_question_is_embedded_only_once() -> None:
    question = "What is the one-hour average CO2 limit?"
    source, embedder = hybrid({question: [0.1, 0.99, 0.0]})

    source.search(question, k=3)
    source.search(question, k=3)

    assert embedder.calls == [[question]]


def test_a_passage_without_a_vector_can_still_be_found_by_its_words() -> None:
    lexical = RagKnowledgeSource(CHUNKS, GLOSSARY)
    source = HybridKnowledgeSource(
        lexical, vectors(include=[*CO2_LIMIT, *HEADACHE]), FakeEmbedder({}), min_similarity=0.5
    )

    results = source.search("What is the noise limit in the crew quarters?", k=3)

    assert [r.requirement_ref for r in results] == ["V2 6079"]


class TestChoosingTheSource:
    def prepare(self, tmp_path: Path, model: str | None) -> Path:
        index = tmp_path / "chunks.jsonl"
        JsonlChunkStore(index).add(CHUNKS)
        if model is not None:
            vectors(model=model).save(tmp_path / "embeddings.json")
        return index

    def test_without_vectors_it_is_the_lexical_search(self, tmp_path: Path) -> None:
        index = self.prepare(tmp_path, model=None)

        source = build_knowledge_source(index, GLOSSARY, FakeEmbedder({}))

        assert isinstance(source, RagKnowledgeSource)

    def test_vectors_from_another_model_are_not_used(self, tmp_path: Path) -> None:
        index = self.prepare(tmp_path, model="other-model")

        source = build_knowledge_source(index, GLOSSARY, FakeEmbedder({}, model="fake"))

        assert isinstance(source, RagKnowledgeSource)

    def test_with_vectors_of_the_same_model_it_is_hybrid(self, tmp_path: Path) -> None:
        index = self.prepare(tmp_path, model="fake")

        source = build_knowledge_source(index, GLOSSARY, FakeEmbedder({}, model="fake"))

        assert isinstance(source, HybridKnowledgeSource)
