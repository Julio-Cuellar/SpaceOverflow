"""Text terms: lowercase words, English plural stemming and term counts for passage search."""

from __future__ import annotations

import re
from collections import Counter

from spaceapp.modules.knowledge.domain.search import normalize

_WORD = re.compile(r"[a-z0-9]+")
MIN_TERM_LENGTH = 3


def words(text: str) -> list[str]:
    """Lowercase words. "CO₂" becomes "co2"."""
    return _WORD.findall(normalize(text))


def stem(word: str) -> str:
    """Removes the English plural so "lasts" and "last", or "headaches" and "headache", match.

    It is applied equally to the question and to the indexed text, so it does not need to be
    linguistically perfect, only consistent.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def token_counts(text: str, min_length: int = MIN_TERM_LENGTH) -> Counter[str]:
    """Frequency of each term, already without plurals. BM25 scoring needs it."""
    stemmed = (stem(word) for word in words(text))
    return Counter(word for word in stemmed if len(word) >= min_length)


def terms(text: str, min_length: int = MIN_TERM_LENGTH) -> frozenset[str]:
    return frozenset(token_counts(text, min_length))


def content_word_count(text: str) -> int:
    """Words with letters and at least 3 characters. A title or an index has almost none."""
    return sum(1 for word in words(text) if len(word) >= 3 and any(ch.isalpha() for ch in word))
