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
    """Estados de una intervención, por voz o por texto (máquina de estados del asistente)."""

    TYPED = "TYPED"  # ESCRITA: texto tecleado, listo para confirmar
    RECEIVED = "RECEIVED"  # RECIBIDA: audio guardado
    TRANSCRIBING = "TRANSCRIBING"  # TRANSCRIBIENDO
    TRANSCRIBED = "TRANSCRIBED"  # TRANSCRITA: texto editable a la espera de confirmar
    NO_TRANSCRIPT = "NO_TRANSCRIPT"  # SIN_TRANSCRIPCION: sin modelo, fallo o sin habla
    CONFIRMED = "CONFIRMED"  # CONFIRMADA
    CONSULTING = "CONSULTING"  # CONSULTANDO: el orquestador trabaja
    ANSWERED = "ANSWERED"  # RESPONDIDA: con pasajes y citas
    NO_INFO = "NO_INFO"  # SIN_INFORMACION: ningún pasaje respalda
    TEMPLATE_ANSWER = "TEMPLATE_ANSWER"  # RESPUESTA_DE_PLANTILLA: el orquestador no pudo
    FAILED = "FAILED"  # FALLIDA: ni siquiera la plantilla
    DISCARDED = "DISCARDED"  # DESCARTADA


class TurnEvent(StrEnum):
    TRANSCRIBE = "TRANSCRIBE"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    TRANSCRIPT_FAILED = "TRANSCRIPT_FAILED"
    CONFIRM = "CONFIRM"
    DISCARD = "DISCARD"
    CONSULT = "CONSULT"
    ANSWERED = "ANSWERED"
    NO_INFO = "NO_INFO"
    FALLBACK_ANSWERED = "FALLBACK_ANSWERED"
    FAILED = "FAILED"


_S = UtteranceStatus
_E = TurnEvent
_READY_FOR_CREW = (_S.TYPED, _S.TRANSCRIBED, _S.NO_TRANSCRIPT)

# Única fuente de verdad de las transiciones. Lo que no está aquí no puede ocurrir.
TRANSITIONS: dict[tuple[UtteranceStatus, TurnEvent], UtteranceStatus] = {
    (_S.RECEIVED, _E.TRANSCRIBE): _S.TRANSCRIBING,
    (_S.TRANSCRIBING, _E.TRANSCRIPT_READY): _S.TRANSCRIBED,
    (_S.TRANSCRIBING, _E.TRANSCRIPT_FAILED): _S.NO_TRANSCRIPT,
    **{(state, _E.CONFIRM): _S.CONFIRMED for state in _READY_FOR_CREW},
    **{(state, _E.DISCARD): _S.DISCARDED for state in _READY_FOR_CREW},
    (_S.CONFIRMED, _E.CONSULT): _S.CONSULTING,
    (_S.CONSULTING, _E.ANSWERED): _S.ANSWERED,
    (_S.CONSULTING, _E.NO_INFO): _S.NO_INFO,
    (_S.CONSULTING, _E.FALLBACK_ANSWERED): _S.TEMPLATE_ANSWER,
    (_S.CONSULTING, _E.FAILED): _S.FAILED,
}

INITIAL_STATES = frozenset({_S.RECEIVED, _S.TYPED})
TERMINAL_STATES = frozenset({_S.ANSWERED, _S.NO_INFO, _S.TEMPLATE_ANSWER, _S.FAILED, _S.DISCARDED})
# Estados en los que la pregunta ya se confirmó: no se vuelve a preguntar.
CONFIRMED_OR_LATER = frozenset(
    {_S.CONFIRMED, _S.CONSULTING, _S.ANSWERED, _S.NO_INFO, _S.TEMPLATE_ANSWER, _S.FAILED}
)


class InvalidTransitionError(RuntimeError):
    """El evento no es válido en el estado actual. El estado no cambia."""


def transition(state: UtteranceStatus, event: TurnEvent) -> UtteranceStatus:
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise InvalidTransitionError(f"{event} no es válido en el estado {state}") from None


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
