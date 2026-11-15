"""Kokoro-82M (ONNX) as the output voice. The real model is not loaded here: a fake is injected."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Any

from spaceapp.modules.assistant.adapters.outbound.kokoro import (
    LANGUAGE,
    VOICE,
    KokoroTextToSpeech,
    build_text_to_speech,
)
from spaceapp.modules.assistant.adapters.outbound.null_tts import NullTextToSpeech

RATE = 24_000


class FakeKokoro:
    def __init__(self, samples: list[float] | None = None) -> None:
        self._samples = samples if samples is not None else [0.0, 0.5, -0.5, 1.0]
        self.calls: list[dict[str, Any]] = []

    def create(self, text: str, voice: str, speed: float, lang: str) -> tuple[list[float], int]:
        self.calls.append({"text": text, "voice": voice, "speed": speed, "lang": lang})
        return self._samples, RATE


def test_the_model_is_not_loaded_until_the_first_phrase() -> None:
    loaded: list[int] = []

    def factory() -> FakeKokoro:
        loaded.append(1)
        return FakeKokoro()

    tts = KokoroTextToSpeech(factory)
    assert loaded == []

    tts.speak("one")
    tts.speak("two")

    assert loaded == [1]


def test_it_returns_a_mono_16_bit_wav_at_the_models_sample_rate() -> None:
    audio = KokoroTextToSpeech(lambda: FakeKokoro([0.0, 0.5, -0.5, 1.0])).speak("hi")

    assert audio is not None
    with wave.open(io.BytesIO(audio)) as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == RATE
        assert wav.getnframes() == 4


def test_samples_are_scaled_and_clipped_to_16_bit() -> None:
    audio = KokoroTextToSpeech(lambda: FakeKokoro([0.5, 2.0, -2.0])).speak("hi")

    assert audio is not None
    with wave.open(io.BytesIO(audio)) as wav:
        frames = wav.readframes(3)
    values = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in (0, 2, 4)]
    assert values == [16383, 32767, -32768]


def test_it_speaks_in_english_with_the_default_voice() -> None:
    model = FakeKokoro()

    KokoroTextToSpeech(lambda: model).speak("The limit is three.")

    assert model.calls == [
        {"text": "The limit is three.", "voice": VOICE, "speed": 1.0, "lang": LANGUAGE}
    ]
    assert VOICE == "af_heart"
    assert LANGUAGE == "en-us"


def test_there_is_nothing_to_say_for_an_empty_text() -> None:
    model = FakeKokoro()

    assert KokoroTextToSpeech(lambda: model).speak("   ") is None
    assert model.calls == []


def test_without_the_library_the_builder_falls_back_to_the_null_adapter(tmp_path: Path) -> None:
    def missing() -> Any:
        raise ImportError("kokoro_onnx")

    assert isinstance(build_text_to_speech(tmp_path, importer=missing), NullTextToSpeech)


def test_without_the_model_files_the_builder_falls_back_to_the_null_adapter(tmp_path: Path) -> None:
    assert isinstance(build_text_to_speech(tmp_path, importer=lambda: FakeKokoro), NullTextToSpeech)


def test_with_library_and_files_the_builder_returns_kokoro_without_loading_the_model(
    tmp_path: Path,
) -> None:
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"x")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"x")
    created: list[tuple[str, str]] = []

    class FakeClass:
        def __init__(self, model_path: str, voices_path: str) -> None:
            created.append((Path(model_path).name, Path(voices_path).name))

    tts = build_text_to_speech(tmp_path, importer=lambda: FakeClass)

    assert isinstance(tts, KokoroTextToSpeech)
    assert tts.available is True
    assert created == []  # carga perezosa
