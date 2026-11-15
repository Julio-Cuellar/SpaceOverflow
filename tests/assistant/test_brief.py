from __future__ import annotations

from spaceapp.modules.assistant.application.brief import MAX_CHARS, brief

PRESSURE = (
    "Carbon Dioxide Levels), the lowest achievable cabin pressure is 5.0 psia (see Figure 6.2-1). "
    "Total pressure must be considered in conjunction with O2 and CO2 requirements. "
    "Under certain spacesuit operations (e.g., DCS treatment, leak checks), the crewmember may be "
    "exposed to pressures above or below this range for a limited period of time.] Figure 6.2-1"
)


def test_a_short_passage_is_left_as_it_is() -> None:
    text = "The system shall limit the average 1-hour CO2 partial pressure to 3 mmHg."

    assert brief(text, "What is the CO2 limit?") == text


def test_keeps_the_sentence_that_answers_the_question() -> None:
    result = brief(PRESSURE, "What is the minimum cabin pressure?")

    assert "lowest achievable cabin pressure is 5.0 psia" in result
    assert "crewmember" not in result


def test_a_long_sentence_is_cut_around_the_figure_not_at_the_start() -> None:
    sentence = (
        "Designers and physiologists must evaluate and trade off the various atmospheric "
        "combinations and also consider many other factors that are listed elsewhere in this "
        "document before choosing a value, so given the need to maintain a diluent gas at 30% "
        "while maintaining normoxia the lowest achievable cabin pressure is 5.0 psia and then "
        "some more words follow that say nothing useful about the question that was asked."
    )

    result = brief(sentence, "What is the minimum cabin pressure?")

    assert "5.0 psia" in result
    assert len(result) <= MAX_CHARS + 2
    assert result.startswith("…")


def test_the_result_never_exceeds_the_limit_plus_the_ellipses() -> None:
    assert len(brief(PRESSURE * 5, "cabin pressure")) <= MAX_CHARS + 2


def test_without_any_word_in_common_it_starts_the_passage() -> None:
    text = "Lorem ipsum dolor sit amet. " * 30

    result = brief(text, "¿Cuál es el límite?")

    assert result.startswith("Lorem ipsum")
    assert len(result) <= MAX_CHARS + 2


def test_the_repeated_page_header_is_dropped() -> None:
    text = "NASA-STD-3001, VOLUME 2, REVISION F 54 of 55 6.2.2 Atmospheric Pressure shall be kept."

    assert "54 of 55" not in brief(text, "pressure")
