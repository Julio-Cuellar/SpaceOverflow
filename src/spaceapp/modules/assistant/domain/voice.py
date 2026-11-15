"""Valores de la entrada por voz. Sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

# Tipos de audio que acepta la ruta de voz (plan, F14): lo que graba `MediaRecorder` y WAV.
_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
}


class UtteranceStatus(StrEnum):
    RECEIVED = "RECEIVED"
    TRANSCRIBED = "TRANSCRIBED"
    NO_TRANSCRIPT = "NO_TRANSCRIPT"
    CONFIRMED = "CONFIRMED"


class UnsupportedAudioError(ValueError):
    """El audio está vacío o no es webm ni wav."""


class UnknownUtteranceError(LookupError):
    """No existe una intervención con ese id."""


class AlreadyConfirmedError(RuntimeError):
    """La intervención ya se confirmó: no se vuelve a preguntar."""


@dataclass(frozen=True)
class Transcript:
    text: str
    confidence: float | None
    language: str | None


@dataclass(frozen=True)
class Utterance:
    id: UUID
    conversation_id: UUID
    status: UtteranceStatus
    text: str = ""
    confidence: float | None = None
    reason: str | None = None
    audio_path: str | None = None


def audio_extension(content_type: str) -> str:
    """Extensión del archivo para un tipo de audio, ignorando parámetros como `;codecs=opus`."""
    base = content_type.split(";", 1)[0].strip().lower()
    try:
        return _EXTENSIONS[base]
    except KeyError:
        raise UnsupportedAudioError(f"tipo de audio no admitido: {content_type!r}") from None
