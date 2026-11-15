"""Voz con confirmación (plan, F14): transcribir no es actuar.

Reglas:
- Recibir el audio responde de inmediato; la transcripción va aparte.
- Lo transcrito queda como texto editable. **Nada se pregunta al asistente sin confirmar.**
- Sin modelo de voz, o si falla, la tripulación escribe la pregunta: el flujo sigue igual.
- Una emergencia no depende de la voz: este módulo no toca alertas.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from spaceapp.modules.assistant.application.ask import AskAssistant, AskOutcome, AskResult
from spaceapp.modules.assistant.domain.voice import (
    AlreadyConfirmedError,
    UnknownUtteranceError,
    UnsupportedAudioError,
    Utterance,
    UtteranceStatus,
    audio_extension,
)
from spaceapp.modules.assistant.ports import AudioStore, SpeechToText, UtteranceRepository

__all__ = [
    "AlreadyConfirmedError",
    "ConfirmUtterance",
    "SubmitAudio",
    "UnknownUtteranceError",
    "UnsupportedAudioError",
]

NO_MODEL = "No hay modelo de voz: escribe tu pregunta como texto."
FAILED = "La transcripción falló: escribe tu pregunta como texto."
NO_SPEECH = "No se oyó nada: repite o escribe tu pregunta como texto."


class SubmitAudio:
    def __init__(
        self, *, stt: SpeechToText, store: AudioStore, utterances: UtteranceRepository
    ) -> None:
        self._stt = stt
        self._store = store
        self._utterances = utterances

    def submit(self, conversation_id: UUID, audio: bytes, content_type: str) -> UUID:
        """Guarda el audio y devuelve el `utterance_id` sin transcribir (responde 202)."""
        extension = audio_extension(content_type)
        if not audio:
            raise UnsupportedAudioError("el audio está vacío")
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
        """Transcribe en segundo plano. Nunca lanza por un fallo del modelo: deja el motivo."""
        utterance = self._utterances.get(utterance_id)
        if utterance.status is not UtteranceStatus.RECEIVED:
            return utterance
        done = self._transcribe(utterance)
        self._utterances.update(done)
        return done

    def _transcribe(self, utterance: Utterance) -> Utterance:
        if not self._stt.available:
            return replace(utterance, status=UtteranceStatus.NO_TRANSCRIPT, reason=NO_MODEL)
        try:
            audio = _read(utterance.audio_path)
            transcript = self._stt.transcribe(audio, _content_type(utterance.audio_path))
        except Exception:  # el modelo puede fallar por muchas causas; la voz nunca es obligatoria
            return replace(utterance, status=UtteranceStatus.NO_TRANSCRIPT, reason=FAILED)
        if transcript is None or not transcript.text.strip():
            return replace(utterance, status=UtteranceStatus.NO_TRANSCRIPT, reason=NO_SPEECH)
        return replace(
            utterance,
            status=UtteranceStatus.TRANSCRIBED,
            text=transcript.text,
            confidence=transcript.confidence,
        )


def _read(path: str | None) -> bytes:
    if path is None:
        raise FileNotFoundError("la intervención no tiene audio")
    with open(path, "rb") as handle:
        return handle.read()


def _content_type(path: str | None) -> str:
    return "audio/webm" if path is not None and path.endswith(".webm") else "audio/wav"


class ConfirmUtterance:
    def __init__(self, *, utterances: UtteranceRepository, ask: AskAssistant) -> None:
        self._utterances = utterances
        self._ask = ask

    def confirm(self, utterance_id: UUID, text: str) -> AskResult:
        """Pregunta al asistente con el texto que la tripulación confirmó (editado o escrito)."""
        utterance = self._utterances.get(utterance_id)
        if utterance.status is UtteranceStatus.CONFIRMED:
            raise AlreadyConfirmedError(str(utterance_id))
        result = self._ask(utterance.conversation_id, text)
        if result.outcome is not AskOutcome.EMPTY_QUESTION:
            self._utterances.update(
                replace(utterance, status=UtteranceStatus.CONFIRMED, text=text.strip())
            )
        return result
