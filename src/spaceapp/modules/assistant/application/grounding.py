"""Cifras de una respuesta que ninguna fuente respalda. Función pura.

Un modelo pequeño puede inventar una cifra («above 9.9 mmHg») aunque cite pasajes. La comprobación
no entiende el texto: busca cada número de la respuesta en los pasajes citados, la pregunta y las
alertas. No detecta una cifra real atribuida a lo que no es (por ejemplo, la banda de 63 Hz de una
tabla leída como el límite de ruido): para eso hace falta revisar la respuesta contra el pasaje.
"""

from __future__ import annotations

import re

# Un número no pegado a una letra («CO2», «ppO2», «H2O» son fórmulas) ni a otro número.
_NUMBER = re.compile(r"(?<![A-Za-z\d.,])\d+(?:[.,]\d+)*")
_THOUSANDS = re.compile(r"^\d{1,3}(?:,\d{3})+$")


def _normalise(raw: str) -> str:
    """«3,035» (miles) y «3035» coinciden; «2,5» (decimal) y «2.50» coinciden con «2.5»."""
    if _THOUSANDS.match(raw):
        return raw.replace(",", "")
    value = raw.replace(",", ".")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value


def figures(text: str) -> set[str]:
    return {_normalise(match) for match in _NUMBER.findall(text)}


def unsupported_figures(answer: str, *sources: str) -> list[str]:
    """Cifras de la respuesta que no aparecen en ninguna fuente, ordenadas."""
    supported: set[str] = set()
    for source in sources:
        supported |= figures(source)
    return sorted(figures(answer) - supported)
