"""Glosario español-inglés: expande una pregunta en español con los términos de los documentos."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from spaceapp.modules.knowledge.domain.search import normalize

_WORD = re.compile(r"[a-z0-9]+")
MIN_TERM_LENGTH = 3


def words(text: str) -> list[str]:
    """Palabras en minúsculas y sin acentos. «CO₂» queda como «co2»."""
    return _WORD.findall(normalize(text))


def stem(word: str) -> str:
    """Quita el plural inglés para que «lasts» y «last», o «headaches» y «headache», coincidan.

    Se aplica igual a la pregunta, al glosario y al texto indexado, así que no hace falta que
    sea lingüísticamente perfecto, solo coherente.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def token_counts(text: str, min_length: int = MIN_TERM_LENGTH) -> Counter[str]:
    """Frecuencia de cada término, ya sin plurales. La necesita el puntaje BM25."""
    stemmed = (stem(word) for word in words(text))
    return Counter(word for word in stemmed if len(word) >= min_length)


def terms(text: str, min_length: int = MIN_TERM_LENGTH) -> frozenset[str]:
    return frozenset(token_counts(text, min_length))


def content_word_count(text: str) -> int:
    """Palabras con letras de al menos 3 caracteres. Un título o un índice casi no tiene."""
    return sum(1 for word in words(text) if len(word) >= 3 and any(ch.isalpha() for ch in word))


class Glossary:
    def __init__(self, entries: Sequence[tuple[Sequence[str], Sequence[str]]]) -> None:
        # Cada frase en español se guarda como palabras separadas por un espacio.
        self._entries = [
            ([" ".join(words(phrase)) for phrase in spanish], list(english))
            for spanish, english in entries
        ]

    def explain(self, question: str) -> tuple[frozenset[str], frozenset[str]]:
        """(términos en inglés, palabras en español que el glosario ya tradujo).

        Las segundas no deben contar como «palabras de la pregunta sin cubrir»: ya están
        representadas por su traducción.
        """
        padded = f" {' '.join(words(question))} "
        english: set[str] = set()
        consumed: set[str] = set()
        for spanish, translations in self._entries:
            for phrase in spanish:
                if phrase and f" {phrase} " in padded:
                    consumed |= {stem(word) for word in phrase.split()}
                    for translation in translations:
                        english |= terms(translation)
        return frozenset(english), frozenset(consumed)

    def expand(self, question: str) -> frozenset[str]:
        """Términos en inglés de todas las frases en español que aparecen en la pregunta."""
        return self.explain(question)[0]
