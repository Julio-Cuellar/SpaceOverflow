"""Kokoro-82M (ONNX) on CPU: text to speech without internet or GPU.

The library and the model are loaded on first use, not at startup: without them the system keeps
the null adapter and the answer is only read on screen. The audio comes out as a 16-bit mono WAV
made with the standard library (no `numpy` or `soundfile` in this adapter).
"""

from __future__ import annotations

import io
import threading
import wave
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Any

from spaceapp.modules.assistant.adapters.outbound.null_tts import NullTextToSpeech
from spaceapp.modules.assistant.ports import TextToSpeech

VOICE = "af_heart"
LANGUAGE = "en-us"
MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"


class KokoroTextToSpeech:
    available = True

    def __init__(self, model_factory: Callable[[], Any]) -> None:
        self._factory = model_factory
        self._model: Any | None = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        with self._lock:
            if self._model is None:
                self._model = self._factory()
            return self._model

    def speak(self, text: str) -> bytes | None:
        if not text.strip():
            return None
        samples, rate = self._load().create(text, voice=VOICE, speed=1.0, lang=LANGUAGE)
        pcm = array("h", (max(-32768, min(32767, int(float(x) * 32767))) for x in samples))
        if pcm.itemsize != 2:  # pragma: no cover - `h` is 16 bits on every platform in use
            raise RuntimeError("the size of `short` is not 16 bits")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(rate))
            wav.writeframes(pcm.tobytes())
        return buffer.getvalue()


def _import_kokoro() -> Any:
    from kokoro_onnx import Kokoro

    return Kokoro


def build_text_to_speech(
    model_dir: Path, importer: Callable[[], Any] = _import_kokoro
) -> TextToSpeech:
    """Kokoro if the library and the two model files are there; otherwise, the null adapter."""
    model_path = model_dir / MODEL_FILE
    voices_path = model_dir / VOICES_FILE
    if not (model_path.exists() and voices_path.exists()):
        return NullTextToSpeech()
    try:
        model_class = importer()
    except ImportError:
        return NullTextToSpeech()
    return KokoroTextToSpeech(lambda: model_class(str(model_path), str(voices_path)))
