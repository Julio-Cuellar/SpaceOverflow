"""¿La redacción del modelo está en inglés? Función pura, sin librerías.

El asistente siempre responde en inglés, pero un modelo pequeño contesta en el idioma de la
pregunta aunque se le pida lo contrario. La comprobación cuenta palabras de función (artículos,
preposiciones, conjunciones) de cada idioma; solo distingue inglés de español.
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
    """Falso solo si hay claramente más palabras de función del español que del inglés."""
    words = _WORD.findall(text.lower())
    english = sum(1 for word in words if word in _ENGLISH)
    spanish = sum(1 for word in words if word in _SPANISH)
    return spanish < 2 or english >= spanish
