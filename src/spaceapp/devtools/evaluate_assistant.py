"""Evalúa el asistente completo (n8n + Ollama + RAG) con las preguntas del RAG.

Pregunta por `POST /dev/ask` del servidor de desarrollo y juzga con las mismas expectativas que la
evaluación de la búsqueda. Una pregunta fuera de alcance solo pasa si el turno cierra en `NO_INFO`
y sin citas: cualquier otra cosa sería una respuesta sin fuente.

    python -m spaceapp.devtools.evaluate_assistant --questions data/knowledge/eval_questions.json
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from spaceapp.modules.knowledge.evaluate import EvalCase, load_cases

K = 3
ANSWER_STATES = {"ANSWERED", "TEMPLATE_ANSWER"}


@dataclass(frozen=True)
class Verdict:
    passed: bool
    state: str
    composed_by: str
    degraded: bool


@dataclass
class Summary:
    in_scope: int = 0
    hits: int = 0
    out_of_scope: int = 0
    leaks: int = 0
    misses: list[str] = field(default_factory=list)
    leaked: list[str] = field(default_factory=list)
    states: Counter[str] = field(default_factory=Counter)
    degraded: int = 0
    latencies: list[float] = field(default_factory=list)

    @property
    def mean_latency_s(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0


def judge(case: EvalCase, answer: dict[str, Any]) -> Verdict:
    state = str(answer["state"])
    citations = answer.get("citations", [])[:K]
    if case.out_of_scope:
        passed = state == "NO_INFO" and not answer.get("citations")
    else:
        passed = state in ANSWER_STATES and any(
            (not case.expected_documents or c["document_code"] in case.expected_documents)
            and all(text.lower() in c["excerpt"].lower() for text in case.expected_contains)
            for c in citations
        )
    return Verdict(
        passed=passed,
        state=state,
        composed_by=str(answer.get("composed_by", "")),
        degraded=bool(answer.get("degraded", False)),
    )


def run(cases: Sequence[EvalCase], ask: Callable[[str], tuple[dict[str, Any], float]]) -> Summary:
    summary = Summary()
    for case in cases:
        answer, seconds = ask(case.question)
        verdict = judge(case, answer)
        summary.states[verdict.state] += 1
        summary.degraded += verdict.degraded
        summary.latencies.append(seconds)
        if case.out_of_scope:
            summary.out_of_scope += 1
            if not verdict.passed:
                summary.leaks += 1
                summary.leaked.append(case.question)
        else:
            summary.in_scope += 1
            if verdict.passed:
                summary.hits += 1
            else:
                summary.misses.append(case.question)
    return summary


def _http_ask(base_url: str, timeout_s: float) -> Callable[[str], tuple[dict[str, Any], float]]:
    def ask(question: str) -> tuple[dict[str, Any], float]:
        request = urllib.request.Request(
            f"{base_url}/dev/ask",
            data=json.dumps({"text": question}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body: dict[str, Any] = json.loads(response.read())
        return body, time.monotonic() - started

    return ask


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa el asistente completo.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()

    cases = load_cases(args.questions)
    ask = _http_ask(args.url, args.timeout)

    def logged(question: str) -> tuple[dict[str, Any], float]:
        answer, seconds = ask(question)
        print(f"  [{seconds:5.1f} s] {answer['state']:<16} {question}", flush=True)
        return answer, seconds

    summary = run(cases, logged)
    print(f"Aciertos: {summary.hits} de {summary.in_scope}")
    for question in summary.misses:
        print(f"  Sin acierto: {question}")
    print(f"Fuera de alcance respondidas: {summary.leaks} de {summary.out_of_scope}")
    for question in summary.leaked:
        print(f"  Respondida sin tener fuente: {question}")
    print(f"Estados: {dict(summary.states)} · degradadas: {summary.degraded}")
    print(f"Latencia media: {summary.mean_latency_s:.1f} s")
    return 0 if not summary.leaks else 1


if __name__ == "__main__":
    raise SystemExit(main())
