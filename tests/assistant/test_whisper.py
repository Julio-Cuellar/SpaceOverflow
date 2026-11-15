"""Local Whisper adapter. The real model is not loaded here: a fake one is injected."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pytest

from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.adapters.outbound.whisper import (
    MEDICAL_TERMS_PROMPT,
    WhisperSpeechToText,
    build_speech_to_text,
)


@dataclass
class Segment:
    text: str
    avg_logprob: float = -0.1


@dataclass
class Info:
    language: str = "en"


class FakeModel:
    def __init__(self, segments: Iterable[Segment]) -> None:
        self._segments = list(segments)
        self.kwargs: dict[str, Any] = {}

    def transcribe(self, audio: Any, **kwargs: Any) -> tuple[Iterable[Segment], Info]:
        self.kwargs = kwargs
        return iter(self._segments), Info()


def test_the_model_is_not_loaded_until_the_first_transcription() -> None:
    loaded: list[int] = []

    def factory() -> FakeModel:
        loaded.append(1)
        return FakeModel([Segment(" hello")])

    stt = WhisperSpeechToText(factory)
    assert loaded == []

    stt.transcribe(b"audio", "audio/wav")
    stt.transcribe(b"audio", "audio/wav")

    assert loaded == [1]


def test_it_joins_the_segments_into_one_text() -> None:
    model = FakeModel([Segment(" I am short"), Segment(" of breath.")])

    transcript = WhisperSpeechToText(lambda: model).transcribe(b"audio", "audio/wav")

    assert transcript is not None
    assert transcript.text == "I am short of breath."
    assert transcript.language == "en"


def test_the_confidence_comes_from_the_segment_probabilities() -> None:
    model = FakeModel([Segment("a", avg_logprob=-0.0), Segment("b", avg_logprob=-0.0)])

    transcript = WhisperSpeechToText(lambda: model).transcribe(b"audio", "audio/wav")

    assert transcript is not None
    assert transcript.confidence == pytest.approx(1.0)


def test_there_is_no_confidence_when_there_are_no_segments() -> None:
    transcript = WhisperSpeechToText(lambda: FakeModel([])).transcribe(b"audio", "audio/wav")

    assert transcript is not None
    assert transcript.text == ""
    assert transcript.confidence is None


def test_it_asks_for_english_and_primes_the_model_with_the_medical_terms() -> None:
    model = FakeModel([Segment("x")])

    WhisperSpeechToText(lambda: model).transcribe(b"audio", "audio/wav")

    assert model.kwargs["language"] == "en"
    assert model.kwargs["initial_prompt"] == MEDICAL_TERMS_PROMPT
    for term in ("hypoxia", "ppCO2", "partial pressure", "cabin"):
        assert term in MEDICAL_TERMS_PROMPT
    assert "presión" not in MEDICAL_TERMS_PROMPT


def test_a_null_adapter_says_it_is_not_available_and_returns_nothing() -> None:
    stt = NullSpeechToText()

    assert stt.available is False
    assert stt.transcribe(b"audio", "audio/wav") is None


def test_without_the_speech_library_the_builder_falls_back_to_the_null_adapter() -> None:
    def missing() -> Any:
        raise ImportError("faster_whisper")

    assert isinstance(build_speech_to_text("small", importer=missing), NullSpeechToText)


def test_with_the_library_the_builder_returns_whisper_without_loading_the_model() -> None:
    created: list[tuple[str, str, str]] = []

    class FakeWhisperModel:
        def __init__(self, size: str, device: str, compute_type: str) -> None:
            created.append((size, device, compute_type))

    stt = build_speech_to_text("small", importer=lambda: FakeWhisperModel)

    assert isinstance(stt, WhisperSpeechToText)
    assert stt.available is True
    assert created == []  # lazy loading: nothing until the first transcription
