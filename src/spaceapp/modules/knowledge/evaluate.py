"""Search evaluation (plan, F12.5): does the expected passage show up, and is nothing answered
without a source?

Measures three things: where the expected passage ranks (recall@k and MRR), that no out-of-scope
question gets a passage (an answer without a source would be an invented protocol) and, with
`--diagnose`, why each case fails: whether the passage is not even in the index, or it is there and
the search does not return it, or returns it late.

Command: `python -m spaceapp.modules.knowledge.evaluate`.
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
# How deep to look for recall and MRR: beyond that it does not help whoever reads the answer.
RANK_DEPTH = 10
# For the diagnosis the search goes very deep: what matters is whether the passage ranks at all.
DIAGNOSE_DEPTH = 500
CUTOFFS = (1, 3, 5, 10)

# Order in which the diagnosis is summarized.
CATEGORIES = (
    "top 3",
    "ranks 4 to 10",
    "rank 11 or later",
    "in the index, not retrieved",
    "not in the index",
)

_THOUSANDS_SEPARATOR = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_documents: tuple[str, ...] = ()
    expected_contains: tuple[str, ...] = ()
    # Alternatives: one of them appearing is enough (e.g. '3,035 kcal' or '12.7 MJ').
    expected_contains_any: tuple[str, ...] = ()
    out_of_scope: bool = False


@lru_cache(maxsize=8192)
def normalize_text(text: str) -> str:
    """Lowercase, a single space, unified 'µ' and no thousands commas ('3,035' -> '3035')."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _THOUSANDS_SEPARATOR.sub("", " ".join(folded.split()))


def _contains(haystack: str, anchor: str) -> bool:
    """The anchor is in the text; a number is not part of another ('25 mg' is not in '125 mg')."""
    pattern = re.escape(anchor)
    if anchor[:1].isdigit():
        pattern = r"(?<!\d)(?<!\d\.)" + pattern
    if anchor[-1:].isdigit():
        pattern += r"(?!\d)"
    return re.search(pattern, haystack) is not None


def matches(case: EvalCase, document_code: str, text: str) -> bool:
    """Is it the expected passage? Accepted document, required text and any of the alternatives."""
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
    # Rank of the first hit of each in-scope question (None if it is not among the first ones).
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
                "case without expectation (no document, no text, not out of scope): "
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
        # Without expected documents any will do: the Technical Briefs cite the same requirements
        # as the standard, so what matters is that the expected text is in the excerpt.
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
            return "not in the index"
        if self.rank is None:
            return "in the index, not retrieved"
        if self.rank <= 3:
            return "top 3"
        if self.rank <= RANK_DEPTH:
            return "ranks 4 to 10"
        return "rank 11 or later"


def diagnose(
    search: PassageSource,
    chunks: Sequence[Chunk],
    cases: Sequence[EvalCase],
    depth: int = DIAGNOSE_DEPTH,
) -> list[CaseDiagnosis]:
    """For each in-scope question: is the passage in the index and at what rank does it show up?

    Separates an ingestion problem (it is not there), a vocabulary problem (it is there but does
    not show up) and an ordering problem (it shows up late): each one is fixed by a different piece.
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
    parser = argparse.ArgumentParser(description="Evaluates the passage search over the index.")
    parser.add_argument("--index", type=Path, default=Path("data/knowledge/index/chunks.jsonl"))
    parser.add_argument(
        "--questions", type=Path, default=Path("data/knowledge/eval_questions.json")
    )
    parser.add_argument("--min-hit-rate", type=float, default=DEFAULT_MIN_HIT_RATE)
    parser.add_argument("-k", type=int, default=3)
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="For each question: whether the passage is in the index and at what rank it shows up.",
    )
    parser.add_argument(
        "--mode",
        choices=("lexical", "hybrid"),
        default="lexical",
        help="lexical: words only; hybrid: words and meaning (needs vectors and Ollama).",
    )
    parser.add_argument(
        "--vectors", type=Path, default=Path("data/knowledge/index/embeddings.json")
    )
    parser.add_argument("--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--url", default=DEFAULT_URL, help="Ollama address")
    args = parser.parse_args(argv)

    chunks = JsonlChunkStore(args.index).all() if args.index.exists() else []
    if not chunks:
        print(
            "There is no index. Run the ingestion first: "
            "python -m spaceapp.modules.knowledge.ingest",
            file=sys.stderr,
        )
        return 2

    if not args.questions.exists():
        print(f"The questions file does not exist: {args.questions}", file=sys.stderr)
        return 2

    lexical = RagKnowledgeSource(chunks)
    source: PassageSource = lexical
    mode = "lexical"
    if args.mode == "hybrid":
        embedder = embedder or OllamaEmbedder(model=args.model, base_url=args.url)
        vectors = VectorIndex.load(args.vectors)
        if vectors is None or vectors.model != embedder.model:
            print(
                f"There are no vectors of model {embedder.model} in {args.vectors}. Compute them: "
                "python -m spaceapp.modules.knowledge.ingest.embed",
                file=sys.stderr,
            )
            return 2
        source = HybridKnowledgeSource(
            lexical, vectors, embedder, min_similarity=args.min_similarity
        )
        mode = f"hybrid ({embedder.model})"
    cases = load_cases(args.questions)
    result = evaluate(source, cases, k=args.k)

    print(f"Mode: {mode}")
    print(f"Hits: {result.hits} of {result.in_scope} ({result.hit_rate:.0%})")
    for question in result.misses:
        print(f"  No hit: {question}")
    recalls = "  ".join(
        f"{'Recall' if cutoff == CUTOFFS[0] else ''}@{cutoff}: {result.recall_at(cutoff):.0%}"
        for cutoff in CUTOFFS
    )
    print(f"{recalls}  MRR: {result.mrr:.2f}")
    print(f"Out of scope answered: {len(result.answered_out_of_scope)} of {result.out_of_scope}")
    for question in result.answered_out_of_scope:
        print(f"  Answered without a source: {question}")

    if args.diagnose:
        diagnoses = diagnose(source, chunks, cases)
        for item in diagnoses:
            print(f"  [{item.category}] {item.question}")
        counts = Counter(item.category for item in diagnoses)
        print("Diagnosis:" + ", ".join(f"{name} {counts[name]}" for name in CATEGORIES))
    return 0 if result.passed(args.min_hit_rate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
