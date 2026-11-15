"""Voice with confirmation (plan, F14): transcribing is not acting.

Rules:
- Receiving the audio answers at once; the transcription goes apart.
- What was transcribed stays as editable text. **Nothing is asked without confirming.**
- Without a voice model, or if it fails, the crew types the question: the flow goes on the same.
- An emergency does not depend on voice: this module does not touch alerts.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from spaceapp.modules.assistant.application.ask import AskAssistant, AskOutcome, AskResult
from spaceapp.modules.assistant.domain.voice import (
    CONFIRMED_OR_LATER,
    AlreadyConfirmedError,
    InvalidTransitionError,
    TurnEvent,
    UnknownUtteranceError,
    UnsupportedAudioError,
    Utterance,
    UtteranceStatus,
    audio_extension,
    transition,
)
from spaceapp.modules.assistant.ports import AudioStore, SpeechToText, UtteranceRepository

__all__ = [
    "AlreadyConfirmedError",
    "ConfirmUtterance",
    "InvalidTransitionError",
    "SubmitAudio",
    "UnknownUtteranceError",
    "UnsupportedAudioError",
]

NO_MODEL = "There is no voice model: type your question as text."
FAILED = "The transcription failed: type your question as text."
NO_SPEECH = "Nothing was heard: repeat or type your question as text."


class SubmitAudio:
    def __init__(
        self, *, stt: SpeechToText, store: AudioStore, utterances: UtteranceRepository
    ) -> None:
        self._stt = stt
        self._store = store
        self._utterances = utterances

    def submit(self, conversation_id: UUID, audio: bytes, content_type: str) -> UUID:
        """Stores the audio and returns the `utterance_id` without transcribing (answers 202)."""
        extension = audio_extension(content_type)
        if not audio:
            raise UnsupportedAudioError("the audio is empty")
        utterance_id = uuid4()
        path = self._store.save(utterance_id, audio, extension)
        self._utterances.add(
            Utterance(
                id=utterance_id,
                conversation_id=conversation_id,
                status=UtteranceStatus.RECEIVED,
                audio_path=path,
            )
        )
        return utterance_id

    def transcribe(self, utterance_id: UUID) -> Utterance:
        """Transcribes in the background. A model failure never raises: it leaves the reason."""
        utterance = self._utterances.get(utterance_id)
        if utterance.status is not UtteranceStatus.RECEIVED:
            return utterance
        working = replace(utterance, status=transition(utterance.status, TurnEvent.TRANSCRIBE))
        self._utterances.update(working)
        done = self._transcribe(working)
        # These are recordings of people: the audio is deleted once there is text or it is known
        # there is none.
        if done.audio_path is not None:
            self._store.delete(done.audio_path)
            done = replace(done, audio_path=None)
        self._utterances.update(done)
        return done

    def _transcribe(self, utterance: Utterance) -> Utterance:
        if not self._stt.available:
            return self._no_transcript(utterance, NO_MODEL)
        try:
            audio = _read(utterance.audio_path)
            transcript = self._stt.transcribe(audio, _content_type(utterance.audio_path))
        except Exception:  # the model can fail for many reasons; voice is never mandatory
            return self._no_transcript(utterance, FAILED)
        if transcript is None or not transcript.text.strip():
            return self._no_transcript(utterance, NO_SPEECH)
        return replace(
            utterance,
            status=transition(utterance.status, TurnEvent.TRANSCRIPT_READY),
            text=transcript.text,
            confidence=transcript.confidence,
        )

    @staticmethod
    def _no_transcript(utterance: Utterance, reason: str) -> Utterance:
        return replace(
            utterance,
            status=transition(utterance.status, TurnEvent.TRANSCRIPT_FAILED),
            reason=reason,
        )


def _read(path: str | None) -> bytes:
    if path is None:
        raise FileNotFoundError("the utterance has no audio")
    with open(path, "rb") as handle:
        return handle.read()


def _content_type(path: str | None) -> str:
    return "audio/webm" if path is not None and path.endswith(".webm") else "audio/wav"


class ConfirmUtterance:
    def __init__(self, *, utterances: UtteranceRepository, ask: AskAssistant) -> None:
        self._utterances = utterances
        self._ask = ask

    def confirm(self, utterance_id: UUID, text: str) -> AskResult:
        """Confirms the text (edited or typed) and consults. It is confirmed only once."""
        utterance = self._utterances.get(utterance_id)
        if utterance.status in CONFIRMED_OR_LATER:
            raise AlreadyConfirmedError(str(utterance_id))
        if not text.strip():
            # Nothing to confirm: there is no transition and the utterance keeps waiting.
            return self._ask(utterance.conversation_id, text)
        return self._consult(utterance, text.strip())

    def confirm_text(self, conversation_id: UUID, text: str) -> AskResult:
        """Typed question: it goes through the same state machine as the voice one."""
        if not text.strip():
            return self._ask(conversation_id, text)
        utterance = Utterance(
            id=uuid4(), conversation_id=conversation_id, status=UtteranceStatus.TYPED
        )
        self._utterances.add(utterance)
        return self._consult(utterance, text.strip())

    def discard(self, utterance_id: UUID) -> Utterance:
        utterance = self._utterances.get(utterance_id)
        discarded = replace(utterance, status=transition(utterance.status, TurnEvent.DISCARD))
        self._utterances.update(discarded)
        return discarded

    def _consult(self, utterance: Utterance, text: str) -> AskResult:
        confirmed = replace(
            utterance, status=transition(utterance.status, TurnEvent.CONFIRM), text=text
        )
        consulting = replace(confirmed, status=transition(confirmed.status, TurnEvent.CONSULT))
        self._utterances.update(consulting)
        try:
            result = self._ask(utterance.conversation_id, text, turn_id=utterance.id)
        except Exception:
            self._utterances.update(
                replace(consulting, status=transition(consulting.status, TurnEvent.FAILED))
            )
            raise
        if result.outcome is AskOutcome.NO_INFO:
            event = TurnEvent.NO_INFO
        elif result.degraded:
            event = TurnEvent.FALLBACK_ANSWERED
        else:
            event = TurnEvent.ANSWERED
        self._utterances.update(replace(consulting, status=transition(consulting.status, event)))
        return result
