from __future__ import annotations

from collections import Counter

from spaceapp.modules.knowledge.domain.glossary import Glossary, terms, token_counts


def test_plural_endings_are_ignored_so_singular_and_plural_match() -> None:
    assert terms("lasts days headaches") == {"last", "day", "headache"}


def test_words_that_end_in_ss_or_are_short_are_left_alone() -> None:
    assert terms("stress pressure gas") == {"stress", "pressure", "gas"}


def test_token_counts_keep_the_frequency_of_each_term() -> None:
    assert token_counts("headache headache fatigue") == Counter({"headache": 2, "fatigue": 1})


def test_explain_returns_the_translation_and_the_spanish_words_it_consumed() -> None:
    glossary = Glossary([(["dolor de cabeza", "duele"], ["headache"])])

    english, consumed = glossary.explain("¿Por qué me duele la cabeza? Me duele mucho")

    assert english == {"headache"}
    assert "duele" in consumed


def test_explain_consumes_nothing_when_no_phrase_matches() -> None:
    assert Glossary([(["dura"], ["lasts"])]).explain("¿Cuánto cuesta?") == (
        frozenset(),
        frozenset(),
    )


def test_the_glossary_expansion_is_normalized_the_same_way() -> None:
    glossary = Glossary([(["dura"], ["lasts"])])

    assert glossary.expand("¿Cuánto dura?") == {"last"}
