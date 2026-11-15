"""Búsqueda de pasajes por términos, sin modelo. Umbral mínimo: por debajo no hay pasaje."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_WORD = re.compile(r"[a-z0-9]+")
MIN_TERM_LENGTH = 4
MIN_SCORE = 1


def normalize(text: str) -> str:
    """Minúsculas y sin acentos. «CO₂» queda como «co2»."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def terms(text: str) -> frozenset[str]:
    return frozenset(
        word for word in _WORD.findall(normalize(text)) if len(word) >= MIN_TERM_LENGTH
    )


@dataclass(frozen=True)
class Indexed[T]:
    item: T
    keywords: frozenset[str]


def rank[T](query: str, indexed: Sequence[Indexed[T]], k: int) -> list[T]:
    """Los pasajes con más términos en común, hasta k. Empates: el orden del catálogo."""
    query_terms = terms(query)
    scored = [
        (len(query_terms & entry.keywords), position, entry.item)
        for position, entry in enumerate(indexed)
    ]
    relevant = [entry for entry in scored if entry[0] >= MIN_SCORE]
    relevant.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item for _, _, item in relevant[:k]]
