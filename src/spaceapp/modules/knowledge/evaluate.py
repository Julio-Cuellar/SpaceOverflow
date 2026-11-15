"""Evaluación de la búsqueda (plan, F12.5): ¿sale el pasaje esperado y nunca se responde sin fuente?

Mide tres cosas: dónde sale el pasaje esperado (recall@k y MRR), que ninguna pregunta fuera de
alcance reciba un pasaje (una respuesta sin fuente sería un protocolo inventado) y, con
`--diagnose`, por qué falla cada caso: si el pasaje ni siquiera está en el índice o si está y la
búsqueda no lo trae, o lo trae tarde.

Comando: `python -m spaceapp.modules.knowledge.evaluate`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.hybrid_source import (
    DEFAULT_MIN_SIMILARITY,
    HybridKnowledgeSource,
)
from spaceapp.modules.knowledge.adapters.outbound.ollama_embedder import (
    DEFAULT_MODEL,
    DEFAULT_URL,
    OllamaEmbedder,
)
from spaceapp.modules.knowledge.adapters.outbound.rag_source import RagKnowledgeSource
from spaceapp.modules.knowledge.domain.model import Citation
from spaceapp.modules.knowledge.ingest.chunking import Chunk
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ingest.vectors import VectorIndex
from spaceapp.modules.knowledge.ports import Embedder, PassageSource

DEFAULT_MIN_HIT_RATE = 0.8
# Hasta qué puesto se mira para el recall y el MRR: más allá no sirve a quien lee la respuesta.
RANK_DEPTH = 10
# Para el diagnóstico se busca muy hondo: interesa saber si el pasaje sale en algún puesto.
DIAGNOSE_DEPTH = 500
CUTOFFS = (1, 3, 5, 10)

# Orden en que se resume el diagnóstico.
CATEGORIES = (
    "top 3",
    "puestos 4 a 10",
    "puesto 11 o más",
    "en el índice, no recuperada",
    "no está en el índice",
)

_THOUSANDS_SEPARATOR = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_documents: tuple[str, ...] = ()
    expected_contains: tuple[str, ...] = ()
    # Alternativas: basta con que aparezca una (p. ej. «3,035 kcal» o «12.7 MJ»).
    expected_contains_any: tuple[str, ...] = ()
    out_of_scope: bool = False


@lru_cache(maxsize=8192)
def normalize_text(text: str) -> str:
    """Minúsculas, un solo espacio, «µ» unificada y sin comas de miles («3,035» → «3035»)."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _THOUSANDS_SEPARATOR.sub("", " ".join(folded.split()))


def _contains(haystack: str, anchor: str) -> bool:
    """El ancla está en el texto; un número no es un trozo de otro («25 mg» no está en «125 mg»)."""
    pattern = re.escape(anchor)
    if anchor[:1].isdigit():
        pattern = r"(?<!\d)(?<!\d\.)" + pattern
    if anchor[-1:].isdigit():
        pattern += r"(?!\d)"
    return re.search(pattern, haystack) is not None


def matches(case: EvalCase, document_code: str, text: str) -> bool:
    """¿Es el pasaje esperado? Documento admitido, texto requerido y alguna de las alternativas."""
    if case.expected_documents and document_code not in case.expected_documents:
        return False
    haystack = normalize_text(text)
    if not all(_contains(haystack, normalize_text(anchor)) for anchor in case.expected_contains):
        return False
    return not case.expected_contains_any or any(
        _contains(haystack, normalize_text(anchor)) for anchor in case.expected_contains_any
    )


@dataclass
class EvalResult:
    in_scope: int = 0
    hits: int = 0
    misses: list[str] = field(default_factory=list)
    out_of_scope: int = 0
    answered_out_of_scope: list[str] = field(default_factory=list)
    # Puesto del primer acierto de cada pregunta en alcance (None si no sale entre los primeros).
    ranks: list[int | None] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        return self.hits / self.in_scope if self.in_scope else 1.0

    def recall_at(self, k: int) -> float:
        if not self.ranks:
            return 1.0
        return sum(1 for rank in self.ranks if rank is not None and rank <= k) / len(self.ranks)

    @property
    def mrr(self) -> float:
        if not self.ranks:
            return 1.0
        return sum(1 / rank for rank in self.ranks if rank) / len(self.ranks)

    def passed(self, min_hit_rate: float = DEFAULT_MIN_HIT_RATE) -> bool:
        return self.hit_rate >= min_hit_rate and not self.answered_out_of_scope


def load_cases(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        EvalCase(
            question=item["question"],
            expected_documents=tuple(item.get("expected_documents", ())),
            expected_contains=tuple(item.get("expected_contains", ())),
            expected_contains_any=tuple(item.get("expected_contains_any", ())),
            out_of_scope=bool(item.get("out_of_scope", False)),
        )
        for item in raw["cases"]
    ]
    for case in cases:
        if not (
            case.out_of_scope
            or case.expected_documents
            or case.expected_contains
            or case.expected_contains_any
        ):
            raise ValueError(
                "caso sin expectativa (ni documento, ni texto, ni fuera de alcance): "
                f"{case.question}"
            )
    return cases


def _first_rank(case: EvalCase, passages: Sequence[Citation]) -> int | None:
    for position, passage in enumerate(passages, start=1):
        if matches(case, passage.document_code, passage.excerpt):
            return position
    return None


def evaluate(search: PassageSource, cases: Sequence[EvalCase], k: int = 3) -> EvalResult:
    result = EvalResult()
    depth = max(k, RANK_DEPTH)
    for case in cases:
        passages = search.search(case.question, depth)
        if case.out_of_scope:
            result.out_of_scope += 1
            if passages:
                result.answered_out_of_scope.append(case.question)
            continue

        result.in_scope += 1
        # Sin documentos esperados vale cualquiera: los Technical Brief citan los mismos requisitos
        # que la norma, así que lo que importa es que el texto esperado esté en el extracto.
        rank = _first_rank(case, passages)
        result.ranks.append(rank)
        if rank is not None and rank <= k:
            result.hits += 1
        else:
            result.misses.append(case.question)
    return result


@dataclass(frozen=True)
class CaseDiagnosis:
    question: str
    indexed: bool
    rank: int | None

    @property
    def category(self) -> str:
        if not self.indexed:
            return "no está en el índice"
        if self.rank is None:
            return "en el índice, no recuperada"
        if self.rank <= 3:
            return "top 3"
        if self.rank <= RANK_DEPTH:
            return "puestos 4 a 10"
        return "puesto 11 o más"


def diagnose(
    search: PassageSource,
    chunks: Sequence[Chunk],
    cases: Sequence[EvalCase],
    depth: int = DIAGNOSE_DEPTH,
) -> list[CaseDiagnosis]:
    """Para cada pregunta en alcance: ¿está el pasaje en el índice y en qué puesto sale?

    Separa un problema de ingesta (no está), de vocabulario (está pero no sale) y de orden (sale
    tarde): cada uno se arregla con una pieza distinta.
    """
    diagnoses: list[CaseDiagnosis] = []
    for case in cases:
        if case.out_of_scope:
            continue
        indexed = any(matches(case, chunk.document_code, chunk.content) for chunk in chunks)
        rank = _first_rank(case, search.search(case.question, depth))
        diagnoses.append(CaseDiagnosis(case.question, indexed, rank))
    return diagnoses


def main(argv: Sequence[str] | None = None, embedder: Embedder | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa la búsqueda de pasajes sobre el índice.")
    parser.add_argument("--index", type=Path, default=Path("data/knowledge/index/chunks.jsonl"))
    parser.add_argument("--glossary", type=Path, default=Path("data/knowledge/glossary_es_en.json"))
    parser.add_argument(
        "--questions", type=Path, default=Path("data/knowledge/eval_questions.json")
    )
    parser.add_argument("--min-hit-rate", type=float, default=DEFAULT_MIN_HIT_RATE)
    parser.add_argument("-k", type=int, default=3)
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Para cada pregunta: si el pasaje está en el índice y en qué puesto sale.",
    )
    parser.add_argument(
        "--mode",
        choices=("lexical", "hybrid"),
        default="lexical",
        help="lexical: solo palabras; hybrid: palabras y significado (necesita vectores y Ollama).",
    )
    parser.add_argument(
        "--vectors", type=Path, default=Path("data/knowledge/index/embeddings.json")
    )
    parser.add_argument("--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--url", default=DEFAULT_URL, help="dirección de Ollama")
    args = parser.parse_args(argv)

    chunks = JsonlChunkStore(args.index).all() if args.index.exists() else []
    if not chunks:
        print(
            "No hay índice. Ejecuta primero la ingesta: "
            "python -m spaceapp.modules.knowledge.ingest",
            file=sys.stderr,
        )
        return 2

    for path, name in ((args.glossary, "glosario"), (args.questions, "archivo de preguntas")):
        if not path.exists():
            print(f"No existe el {name}: {path}", file=sys.stderr)
            return 2

    lexical = RagKnowledgeSource(chunks, args.glossary)
    source: PassageSource = lexical
    mode = "léxico"
    if args.mode == "hybrid":
        embedder = embedder or OllamaEmbedder(model=args.model, base_url=args.url)
        vectors = VectorIndex.load(args.vectors)
        if vectors is None or vectors.model != embedder.model:
            print(
                f"No hay vectores del modelo {embedder.model} en {args.vectors}. Calcúlalos: "
                "python -m spaceapp.modules.knowledge.ingest.embed",
                file=sys.stderr,
            )
            return 2
        source = HybridKnowledgeSource(
            lexical, vectors, embedder, min_similarity=args.min_similarity
        )
        mode = f"híbrido ({embedder.model})"
    cases = load_cases(args.questions)
    result = evaluate(source, cases, k=args.k)

    print(f"Modo: {mode}")
    print(f"Aciertos: {result.hits} de {result.in_scope} ({result.hit_rate:.0%})")
    for question in result.misses:
        print(f"  Sin acierto: {question}")
    recalls = "  ".join(
        f"{'Recall' if cutoff == CUTOFFS[0] else ''}@{cutoff}: {result.recall_at(cutoff):.0%}"
        for cutoff in CUTOFFS
    )
    print(f"{recalls}  MRR: {result.mrr:.2f}")
    print(
        f"Fuera de alcance respondidas: {len(result.answered_out_of_scope)} "
        f"de {result.out_of_scope}"
    )
    for question in result.answered_out_of_scope:
        print(f"  Respondida sin tener fuente: {question}")

    if args.diagnose:
        diagnoses = diagnose(source, chunks, cases)
        for item in diagnoses:
            print(f"  [{item.category}] {item.question}")
        counts = Counter(item.category for item in diagnoses)
        print("Diagnóstico: " + ", ".join(f"{name} {counts[name]}" for name in CATEGORIES))
    return 0 if result.passed(args.min_hit_rate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
