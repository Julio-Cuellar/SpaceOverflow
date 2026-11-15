"""Figures in an answer that no source supports. Pure function.

A small model can invent a figure ('above 9.9 mmHg') even when it cites passages. The check does
not understand the text: it looks for each number of the answer in the cited passages, the
question and the alerts. It does not detect a real figure attributed to the wrong thing (for
example, the 63 Hz band of a table read as the noise limit): that needs reviewing the answer
against the passage.
"""

from __future__ import annotations

import re

# A number not attached to a letter ('CO2', 'ppO2', 'H2O' are formulas) nor to another number.
_NUMBER = re.compile(r"(?<![A-Za-z\d.,])\d+(?:[.,]\d+)*")
_THOUSANDS = re.compile(r"^\d{1,3}(?:,\d{3})+$")


def _normalise(raw: str) -> str:
    """'3,035' (thousands) and '3035' match; '2,5' (decimal) and '2.50' match '2.5'."""
    if _THOUSANDS.match(raw):
        return raw.replace(",", "")
    value = raw.replace(",", ".")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value


def figures(text: str) -> set[str]:
    return {_normalise(match) for match in _NUMBER.findall(text)}


def unsupported_figures(answer: str, *sources: str) -> list[str]:
    """Figures of the answer that appear in no source, sorted."""
    supported: set[str] = set()
    for source in sources:
        supported |= figures(source)
    return sorted(figures(answer) - supported)
