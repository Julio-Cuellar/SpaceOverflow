"""Is the model's wording in English? Pure function, no libraries.

The assistant always answers in English, but a small model answers in the language of the question
even when asked otherwise. The check counts function words (articles, prepositions, conjunctions)
of each language; it only tells English from Spanish.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-záéíóúüñ]+")

_ENGLISH = frozenset(
    [
        "the",
        "of",
        "and",
        "is",
        "are",
        "to",
        "in",
        "for",
        "with",
        "that",
        "this",
        "be",
        "as",
        "by",
        "on",
        "at",
        "from",
        "or",
        "an",
        "it",
        "its",
        "was",
        "were",
        "not",
        "than",
        "which",
        "must",
        "shall",
        "can",
    ]
)
_SPANISH = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "y",
        "que",
        "es",
        "son",
        "en",
        "un",
        "una",
        "por",
        "para",
        "con",
        "se",
        "su",
        "sus",
        "al",
        "lo",
        "como",
        "más",
        "esta",
        "este",
        "estos",
        "debido",
        "entre",
        "sobre",
        "una",
        "cada",
    ]
)


def is_english(text: str) -> bool:
    """False only if there are clearly more Spanish function words than English ones."""
    words = _WORD.findall(text.lower())
    english = sum(1 for word in words if word in _ENGLISH)
    spanish = sum(1 for word in words if word in _SPANISH)
    return spanish < 2 or english >= spanish
