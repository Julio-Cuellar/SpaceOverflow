from __future__ import annotations

import pytest

from spaceapp.modules.assistant.application.language import is_english


@pytest.mark.parametrize(
    "text",
    [
        "The average 1-hour CO2 limit is 3 mmHg.",
        "According to the loaded sources, the crew needs 3,035 kcal per day.",
        "ppCO2 3 mmHg",  # no function words: no reason to reject it
        "",
    ],
)
def test_english_text_is_accepted(text: str) -> None:
    assert is_english(text)


@pytest.mark.parametrize(
    "text",
    [
        "El límite de CO₂ promedio de una hora es de 3 mmHg.",
        "Este límite se estableció debido a evidencia de datos operativos y de investigación.",
        "La tripulación necesita un promedio de 3 035 kcal por día en la misión.",
    ],
)
def test_spanish_text_is_rejected(text: str) -> None:
    assert not is_english(text)


def test_an_english_answer_with_a_spanish_term_is_still_english() -> None:
    assert is_english("The limit applies to the cabin, known in Spanish as la cabina.")
