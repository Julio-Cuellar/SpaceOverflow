"""Glosario español-inglés: expande una pregunta en español con los términos de los documentos."""

from __future__ import annotations

import re
from collections.abc import Sequence

from spaceapp.modules.knowledge.domain.search import normalize

_WORD = re.compile(r"[a-z0-9]+")
MIN_TERM_LENGTH = 3


def words(text: str) -> list[str]:
    """Palabras en minúsculas y sin acentos. «CO₂» queda como «co2»."""
    return _WORD.findall(normalize(text))


def terms(text: str, min_length: int = MIN_TERM_LENGTH) -> frozenset[str]:
    return frozenset(word for word in words(text) if len(word) >= min_length)


class Glossary:
    def __init__(self, entries: Sequence[tuple[Sequence[str], Sequence[str]]]) -> None:
        # Cada frase en español se guarda como palabras separadas por un espacio.
        self._entries = [
            ([" ".join(words(phrase)) for phrase in spanish], list(english))
            for spanish, english in entries
        ]

    def expand(self, question: str) -> frozenset[str]:
        """Términos en inglés de todas las frases en español que aparecen en la pregunta."""
        padded = f" {' '.join(words(question))} "
        found: set[str] = set()
        for spanish, english in self._entries:
            if any(phrase and f" {phrase} " in padded for phrase in spanish):
                for phrase in english:
                    found |= terms(phrase)
        return frozenset(found)
