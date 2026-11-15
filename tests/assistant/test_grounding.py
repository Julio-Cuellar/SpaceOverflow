from __future__ import annotations

import pytest

from spaceapp.modules.assistant.application.grounding import figures, unsupported_figures


def test_a_figure_that_appears_in_a_source_is_supported() -> None:
    answer = "Headache appears between 2.8 and 4.5 mmHg."
    source = "Headaches at levels between 2.8-4.5 mmHg."

    assert unsupported_figures(answer, source) == []


def test_a_figure_that_no_source_has_is_reported() -> None:
    answer = "Headache appears above 9.9 mmHg, and the limit is 3 mmHg."

    assert unsupported_figures(answer, "The limit is 3 mmHg.") == ["9.9"]


@pytest.mark.parametrize(
    ("answer", "source"),
    [
        ("It needs 3035 kcal.", "The requirement is 3,035 kcal per day."),
        ("It needs 3,035 kcal.", "The requirement is 3035 kcal per day."),
        ("About 2.50 mmHg.", "Below 2.5 mmHg."),
        ("Unos 2,5 mmHg.", "Below 2.5 mmHg."),
    ],
)
def test_thousands_separators_decimal_commas_and_trailing_zeros_do_not_matter(
    answer: str, source: str
) -> None:
    assert unsupported_figures(answer, source) == []


def test_numbers_inside_chemical_formulas_are_not_figures() -> None:
    assert figures("CO2 and O2 and ppO2 and H2O") == set()


def test_a_figure_that_is_part_of_a_code_still_counts() -> None:
    assert figures("The limit is NC-40.") == {"40"}


def test_a_figure_is_not_a_piece_of_a_longer_number() -> None:
    assert unsupported_figures("About 25 mg.", "Take 125 mg daily.") == ["25"]


def test_several_sources_are_searched() -> None:
    assert unsupported_figures("It is 3 mmHg for 7 days.", "3 mmHg", "7 days") == []


def test_an_answer_without_figures_is_always_supported() -> None:
    assert unsupported_figures("I don't have that information.", "") == []
