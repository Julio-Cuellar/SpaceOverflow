"""Text read aloud: the body of the answer, without sources and with the units spoken.

A synthetic voice reads 'mmHg', '≤' or 'ppCO2' badly. Here the sources block and the source label
of each template passage are removed, and the most common symbols and units are spelled out. It is
cut at a sentence so it is not minutes of speech. Pure function: the answer on screen does not
change.
"""

from __future__ import annotations

import re

MAX_CHARS = 400

_SOURCES = re.compile(r"\n\s*\n?Sources:.*\Z", re.DOTALL)
# The source label of the template: '(Document · V2 6004 · TB)' at the end of each line.
_LABEL = re.compile(r"\s*\([^()\n]*·[^()\n]*\)\s*$", re.MULTILINE)
_SPOKEN = (
    (re.compile(r"\bppCO2\b|\bppCO₂\b"), "carbon dioxide partial pressure"),
    (re.compile(r"\bCO2\b|\bCO₂\b"), "carbon dioxide"),
    (re.compile(r"\bO2\b|\bO₂\b"), "oxygen"),
    (re.compile(r"\bmmHg\b"), "millimeters of mercury"),
    (re.compile(r"\bkPa\b"), "kilopascals"),
    (re.compile(r"\bpsia\b"), "P S I A"),
    (re.compile(r"≤"), " at most "),
    (re.compile(r"≥"), " at least "),
    (re.compile(r"<"), " less than "),
    (re.compile(r">"), " more than "),
)
_MARKDOWN = re.compile(r"[*_`#]+")
_BRACKETS = re.compile(r"[\[\]]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _cut(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    window = text[:MAX_CHARS]
    ends = [m.end() for m in _SENTENCE_END.finditer(window)]
    if ends and ends[-1] >= MAX_CHARS // 3:
        return window[: ends[-1]].strip()
    cut = window.rfind(" ")
    return window[:cut].strip() if cut > 0 else window.strip()


def speakable(text: str) -> str:
    body = _SOURCES.sub("", text)
    body = _LABEL.sub("", body)
    for pattern, spoken in _SPOKEN:
        body = pattern.sub(spoken, body)
    body = _BRACKETS.sub("", _MARKDOWN.sub("", body))
    body = re.sub(r"^\s*-\s+", "", body, flags=re.MULTILINE)
    body = re.sub(r"\s*\n\s*", " ", body)
    return _cut(re.sub(r"\s{2,}", " ", body).strip())
