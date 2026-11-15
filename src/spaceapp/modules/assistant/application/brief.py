"""Resumen extractivo de un pasaje para la plantilla: la parte que contesta la pregunta.

La plantilla se usa cuando el modelo no contesta, y mostraba cada pasaje entero (600 a 900
caracteres). Aquí se elige la frase que más se parece a la pregunta y, si aún es larga, la ventana
que más términos y cifras reúne. No se reescribe nada: todo lo que sale está literalmente en el
pasaje. Las citas conservan el extracto completo; esto solo cambia lo que se lee en la plantilla.
"""

from __future__ import annotations

import re

MAX_CHARS = 260

_WORD = re.compile(r"[A-Za-z0-9]+")
# El encabezado de cada hoja de la norma («NASA-STD-3001, VOLUME 2, REVISION F 54 of 55»).
_PAGE_HEADER = re.compile(r"NASA-STD-3001,? VOLUME \d,? REVISION [A-Z] \d+ of \d+\s*")
_SENTENCE_END = re.compile(r"(?<=[.;\]])\s+(?=[A-Z\[(])")
_STOP = frozenset(
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
        "what",
        "which",
        "who",
        "how",
        "why",
        "when",
        "where",
        "does",
        "do",
        "can",
        "must",
        "shall",
        "should",
        "would",
        "could",
        "much",
        "many",
        "each",
        "per",
    ]
)


def _terms(text: str) -> set[str]:
    return {
        word.lower().rstrip("s")
        for word in _WORD.findall(text)
        if len(word) > 2 and word.lower() not in _STOP
    }


def _weight(sentence: str, query: set[str]) -> float:
    words = _terms(sentence)
    return len(words & query) + (0.5 if any(c.isdigit() for c in sentence) else 0.0)


def _window(sentence: str, query: set[str]) -> str:
    """La ventana de `MAX_CHARS` con más términos de la pregunta y cifras, entre palabras."""
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", sentence)]
    best_score, best_first = -1.0, 0
    for first, (start, _) in enumerate(words):
        piece = sentence[start : start + MAX_CHARS]
        score = _weight(piece, query)
        if score >= best_score:  # a igualdad, la más tardía: la cifra suele ir tras los términos
            best_score, best_first = score, first
    start = words[best_first][0]
    end = start + MAX_CHARS
    if end < len(sentence):  # termina en una palabra entera
        last = max(i for i, (_, word_end) in enumerate(words) if word_end <= end)
        end = words[last][1]
    else:
        end = len(sentence)
    return (
        ("…" if start > 0 else "")
        + sentence[start:end].strip()
        + ("…" if end < len(sentence) else "")
    )


def _head(text: str) -> str:
    piece = text[:MAX_CHARS]
    cut = piece.rfind(" ")
    return (piece[:cut] if cut > MAX_CHARS // 2 else piece).strip() + "…"


def brief(excerpt: str, question: str) -> str:
    text = _PAGE_HEADER.sub("", excerpt).strip()
    if len(text) <= MAX_CHARS:
        return text
    query = _terms(question)
    sentences = [s for s in _SENTENCE_END.split(text) if s.strip()]
    best = max(sentences, key=lambda s: _weight(s, query), default=text)
    if _weight(best, query) <= 0.5:  # ninguna frase se parece a la pregunta: el comienzo
        return _head(text)
    if len(best) <= MAX_CHARS:
        return best.strip()
    return _window(best, query)
