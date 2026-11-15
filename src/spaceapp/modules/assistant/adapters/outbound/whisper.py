"""Local Whisper with `faster-whisper`: speech to text without internet or GPU (plan, F14.1).

The library and the model are loaded on first use, not at startup: without them the system keeps
working with the null adapter and text input.
"""

from __future__ import annotations

import io
import math
import threading
from collections.abc import Callable
from typing import Any

from spaceapp.modules.assistant.adapters.outbound.null_stt import NullSpeechToText
from spaceapp.modules.assistant.domain.voice import Transcript
from spaceapp.modules.assistant.ports import SpeechToText

# Whisper does better with uncommon terms if it is given a context text containing them.
MEDICAL_TERMS_PROMPT = (
    "A crew member's question about their health and the cabin atmosphere: hypoxia, ppCO2, "
    "partial pressure of oxygen, carbon dioxide, cabin pressure, alert."
)
LANGUAGE = "en"


class WhisperSpeechToText:
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

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        model = self._load()
        segments, info = model.transcribe(
            io.BytesIO(audio),
            language=LANGUAGE,
            initial_prompt=MEDICAL_TERMS_PROMPT,
            vad_filter=True,
        )
        pieces = list(segments)
        text = " ".join(piece.text.strip() for piece in pieces).strip()
        confidence = (
            sum(math.exp(piece.avg_logprob) for piece in pieces) / len(pieces) if pieces else None
        )
        return Transcript(
            text=text, confidence=confidence, language=getattr(info, "language", None)
        )


def _import_whisper_model() -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel


def build_speech_to_text(
    model_size: str, importer: Callable[[], Any] = _import_whisper_model
) -> SpeechToText:
    """Whisper if the library is installed; otherwise, the null adapter (the question is typed)."""
    try:
        model_class = importer()
    except ImportError:
        return NullSpeechToText()
    return WhisperSpeechToText(lambda: model_class(model_size, device="cpu", compute_type="int8"))
