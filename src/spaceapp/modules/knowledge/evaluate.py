"""Search evaluation (architecture plan, F12.5): is the expected passage found, never unsourced?

It measures two things: whether the expected document or text is among the top `k`, and that no
out-of-scope question receives a passage (an answer without a source would be an invented
protocol).

Command: `python -m spaceapp.modules.knowledge.evaluate`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from spaceapp.modules.knowledge.adapters.outbound.rag_source import RagKnowledgeSource
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore
from spaceapp.modules.knowledge.ports import PassageSource

DEFAULT_MIN_HIT_RATE = 0.8


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_documents: tuple[str, ...] = ()
    expected_contains: tuple[str, ...] = ()
    out_of_scope: bool = False


@dataclass
class EvalResult:
    in_scope: int = 0
    hits: int = 0
    misses: list[str] = field(default_factory=list)
    out_of_scope: int = 0
    answered_out_of_scope: list[str] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        return self.hits / self.in_scope if self.in_scope else 1.0

    def passed(self, min_hit_rate: float = DEFAULT_MIN_HIT_RATE) -> bool:
        return self.hit_rate >= min_hit_rate and not self.answered_out_of_scope


def load_cases(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        EvalCase(
            question=item["question"],
            expected_documents=tuple(item.get("expected_documents", ())),
            expected_contains=tuple(item.get("expected_contains", ())),
            out_of_scope=bool(item.get("out_of_scope", False)),
        )
        for item in raw["cases"]
    ]
    for case in cases:
        if not (case.out_of_scope or case.expected_documents or case.expected_contains):
            raise ValueError(
                "case without expectation (no document, no text, not out of scope): "
                f"{case.question}"
            )
    return cases


def evaluate(search: PassageSource, cases: Sequence[EvalCase], k: int = 3) -> EvalResult:
    result = EvalResult()
    for case in cases:
        passages = search.search(case.question, k)
        if case.out_of_scope:
            result.out_of_scope += 1
            if passages:
                result.answered_out_of_scope.append(case.question)
            continue

        result.in_scope += 1
        # With no expected documents any will do: the Technical Briefs cite the same requirements
        # as the standard, so what matters is that the expected text is in the excerpt.
        hit = any(
            (not case.expected_documents or passage.document_code in case.expected_documents)
            and all(text.lower() in passage.excerpt.lower() for text in case.expected_contains)
            for passage in passages[:k]
        )
        if hit:
            result.hits += 1
        else:
            result.misses.append(case.question)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluates passage search over the index.")
    parser.add_argument("--index", type=Path, default=Path("data/knowledge/index/chunks.jsonl"))
    parser.add_argument(
        "--questions", type=Path, default=Path("data/knowledge/eval_questions.json")
    )
    parser.add_argument("--min-hit-rate", type=float, default=DEFAULT_MIN_HIT_RATE)
    parser.add_argument("-k", type=int, default=3)
    args = parser.parse_args(argv)

    if not args.index.exists() or not JsonlChunkStore(args.index).all():
        print(
            "There is no index. Run the ingestion first: "
            "python -m spaceapp.modules.knowledge.ingest",
            file=sys.stderr,
        )
        return 2

    if not args.questions.exists():
        print(f"The questions file does not exist: {args.questions}", file=sys.stderr)
        return 2

    source = RagKnowledgeSource.from_index(args.index)
    result = evaluate(source, load_cases(args.questions), k=args.k)

    print(f"Hits: {result.hits} of {result.in_scope} ({result.hit_rate:.0%})")
    for question in result.misses:
        print(f"  Miss: {question}")
    print(f"Out-of-scope answered: {len(result.answered_out_of_scope)} of {result.out_of_scope}")
    for question in result.answered_out_of_scope:
        print(f"  Answered without a source: {question}")
    return 0 if result.passed(args.min_hit_rate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
