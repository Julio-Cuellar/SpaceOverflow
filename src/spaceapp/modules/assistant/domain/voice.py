"""Values of the voice input. No external dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

# Audio types the voice route accepts (plan, F14): what `MediaRecorder` records, and WAV.
_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
}


class UtteranceStatus(StrEnum):
    """States of an utterance, by voice or by text (the assistant's state machine)."""

    TYPED = "TYPED"  # TYPED: typed text, ready to confirm
    RECEIVED = "RECEIVED"  # RECIBIDA: audio guardado
    TRANSCRIBING = "TRANSCRIBING"  # TRANSCRIBIENDO
    TRANSCRIBED = "TRANSCRIBED"  # TRANSCRIBED: editable text waiting for confirmation
    NO_TRANSCRIPT = "NO_TRANSCRIPT"  # NO_TRANSCRIPT: no model, failure or no speech
    CONFIRMED = "CONFIRMED"  # CONFIRMADA
    CONSULTING = "CONSULTING"  # CONSULTING: the orchestrator is working
    ANSWERED = "ANSWERED"  # ANSWERED: with passages and citations
    NO_INFO = "NO_INFO"  # NO_INFO: no passage supports it
    TEMPLATE_ANSWER = "TEMPLATE_ANSWER"  # TEMPLATE_ANSWER: the orchestrator could not
    FAILED = "FAILED"  # FAILED: not even the template
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

# Single source of truth for the transitions. What is not here cannot happen.
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
# States in which the question was already confirmed: it is not asked again.
CONFIRMED_OR_LATER = frozenset(
    {_S.CONFIRMED, _S.CONSULTING, _S.ANSWERED, _S.NO_INFO, _S.TEMPLATE_ANSWER, _S.FAILED}
)


class InvalidTransitionError(RuntimeError):
    """The event is not valid in the current state. The state does not change."""


def transition(state: UtteranceStatus, event: TurnEvent) -> UtteranceStatus:
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise InvalidTransitionError(f"{event} is not valid in state {state}") from None


class UnsupportedAudioError(ValueError):
    """The audio is empty or is neither webm nor wav."""


class UnknownUtteranceError(LookupError):
    """There is no utterance with that id."""


class AlreadyConfirmedError(RuntimeError):
    """The utterance was already confirmed: it is not asked again."""


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
    """File extension for an audio type, ignoring parameters such as `;codecs=opus`."""
    base = content_type.split(";", 1)[0].strip().lower()
    try:
        return _EXTENSIONS[base]
    except KeyError:
        raise UnsupportedAudioError(f"tipo de audio no admitido: {content_type!r}") from None
