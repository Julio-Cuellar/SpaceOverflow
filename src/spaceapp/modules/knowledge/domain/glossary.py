"""Spanish-English glossary: expands a Spanish question with the terms of the documents."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from spaceapp.modules.knowledge.domain.search import normalize

_WORD = re.compile(r"[a-z0-9]+")
MIN_TERM_LENGTH = 3


def words(text: str) -> list[str]:
    """Lowercase words without accents. 'CO₂' becomes 'co2'."""
    return _WORD.findall(normalize(text))


def stem(word: str) -> str:
    """Removes the English plural so that 'lasts' and 'last', or 'headaches' and 'headache', match.

    It is applied the same to the question, the glossary and the indexed text, so it does not need
    to be linguistically perfect, only consistent.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def token_counts(text: str, min_length: int = MIN_TERM_LENGTH) -> Counter[str]:
    """Frequency of each term, already without plurals. The BM25 score needs it."""
    stemmed = (stem(word) for word in words(text))
    return Counter(word for word in stemmed if len(word) >= min_length)


def terms(text: str, min_length: int = MIN_TERM_LENGTH) -> frozenset[str]:
    return frozenset(token_counts(text, min_length))


def content_word_count(text: str) -> int:
    """Words with letters of at least 3 characters. A title or an index has almost none."""
    return sum(1 for word in words(text) if len(word) >= 3 and any(ch.isalpha() for ch in word))


class Glossary:
    def __init__(self, entries: Sequence[tuple[Sequence[str], Sequence[str]]]) -> None:
        # Each Spanish phrase is stored as words separated by a space.
        self._entries = [
            ([" ".join(words(phrase)) for phrase in spanish], list(english))
            for spanish, english in entries
        ]

    def explain(self, question: str) -> tuple[frozenset[str], frozenset[str]]:
        """(English terms, Spanish words the glossary already translated).

        The latter must not count as 'question words left uncovered': they are already
        represented by their translation.
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
        """English terms of all the Spanish phrases that appear in the question."""
        return self.explain(question)[0]
