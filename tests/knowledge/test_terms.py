from __future__ import annotations

from collections import Counter

from spaceapp.modules.knowledge.domain.terms import content_word_count, terms, token_counts


def test_plural_endings_are_ignored_so_singular_and_plural_match() -> None:
    assert terms("lasts days headaches") == {"last", "day", "headache"}


def test_words_that_end_in_ss_or_are_short_are_left_alone() -> None:
    assert terms("stress pressure gas") == {"stress", "pressure", "gas"}


def test_token_counts_keep_the_frequency_of_each_term() -> None:
    assert token_counts("headache headache fatigue") == Counter({"headache": 2, "fatigue": 1})


def test_terms_are_lowercase_and_subscripts_are_folded() -> None:
    assert terms("CO₂ Limit") == {"co2", "limit"}


def test_content_word_count_ignores_short_words_and_bare_numbers() -> None:
    assert content_word_count("The CO2 limit is 3 mmHg 6.2.2.1") == 4
