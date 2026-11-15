"""Medición de la voz: tasa de error de palabras (WER) entre lo dicho y lo transcrito."""

from __future__ import annotations

import pytest

from spaceapp.devtools.voice_measure import measure, word_error_rate


def test_identical_texts_have_no_errors() -> None:
    assert word_error_rate("what is the cabin pressure", "what is the cabin pressure") == 0.0


def test_case_and_punctuation_do_not_count_as_errors() -> None:
    assert word_error_rate("What is the cabin pressure?", "what is the cabin pressure") == 0.0


def test_a_wrong_word_is_one_error_over_the_expected_length() -> None:
    assert word_error_rate("what is the cabin pressure", "what is the cabin pleasure") == 0.2


def test_a_missing_and_an_extra_word_both_count() -> None:
    assert word_error_rate("a b c d", "a b c") == 0.25
    assert word_error_rate("a b c d", "a b c d e") == 0.25


def test_an_empty_transcript_is_all_errors() -> None:
    assert word_error_rate("a b", "") == 1.0


def test_an_empty_reference_is_rejected() -> None:
    with pytest.raises(ValueError):
        word_error_rate("", "anything")


def test_the_measurement_reports_the_mean_error_and_the_latency_of_each_sample() -> None:
    results = [
        ("what is the cabin pressure", "what is the cabin pressure", 1.0),
        ("why do I have a headache", "why do I have headache", 3.0),
    ]

    summary = measure(results)

    assert summary["samples"] == 2
    assert summary["mean_wer"] == pytest.approx((0.0 + 1 / 6) / 2)
    assert summary["mean_seconds"] == 2.0
    assert summary["max_seconds"] == 3.0
