"""Voice REST routes: raw audio in, editable text out, and nothing is asked without confirming.

    POST /api/v1/voice/utterances?conversation_id=...   body = audio  -> 202 and the `utterance_id`
    GET  /api/v1/voice/utterances/{id}                  state and editable transcript
    POST /api/v1/voice/utterances/{id}/confirm          {"text": ...} -> the assistant's answer
    POST /api/v1/voice/utterances/{id}/discard          discards without asking

The audio goes as a raw body (not `multipart`): no extra dependency is needed. The transcription
runs apart, after answering 202; the client polls the state until `TRANSCRIBED`.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, StringConstraints

from spaceapp.modules.assistant.application.speakable import speakable
from spaceapp.modules.assistant.application.voice import (
    FAILED,
    NO_MODEL,
    NO_SPEECH,
    AlreadyConfirmedError,
    ConfirmUtterance,
    SubmitAudio,
    UnknownUtteranceError,
    UnsupportedAudioError,
)
from spaceapp.modules.assistant.domain.voice import InvalidTransitionError, Utterance
from spaceapp.modules.assistant.ports import TextToSpeech, UtteranceRepository


class ConfirmRequest(BaseModel):
    text: str


class SpeakRequest(BaseModel):
    text: Annotated[str, StringConstraints(max_length=20_000)]


# The client tells "nothing was heard" (repeat) from "the voice service is down" (type instead).
_REASON_CODES = {NO_SPEECH: "NO_SPEECH", FAILED: "FAILED", NO_MODEL: "NO_MODEL"}


def _state(utterance: Utterance) -> dict[str, Any]:
    return {
        "utterance_id": str(utterance.id),
        "status": utterance.status.value,
        "text": utterance.text,
        "confidence": utterance.confidence,
        "reason": utterance.reason,
        "reason_code": _REASON_CODES.get(utterance.reason or ""),
    }


def build_voice_router(
    *, submit: SubmitAudio, confirm: ConfirmUtterance, utterances: UtteranceRepository
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/voice/utterances", tags=["voice"])

    def get_or_404(utterance_id: UUID) -> Utterance:
        try:
            return utterances.get(utterance_id)
        except UnknownUtteranceError:
            raise HTTPException(status_code=404, detail="unknown utterance") from None

    @router.post("", status_code=202)
    async def upload(
        request: Request, conversation_id: UUID, background: BackgroundTasks
    ) -> dict[str, str]:
        audio = await request.body()
        if not audio:
            raise HTTPException(status_code=400, detail="the audio is empty")
        try:
            utterance_id = submit.submit(
                conversation_id, audio, request.headers.get("content-type", "")
            )
        except UnsupportedAudioError as error:
            raise HTTPException(status_code=415, detail=str(error)) from None
        background.add_task(submit.transcribe, utterance_id)
        return {"utterance_id": str(utterance_id)}

    @router.get("/{utterance_id}")
    def state(utterance_id: UUID) -> dict[str, Any]:
        return _state(get_or_404(utterance_id))

    @router.post("/{utterance_id}/confirm")
    def confirm_text(utterance_id: UUID, body: ConfirmRequest) -> dict[str, Any]:
        get_or_404(utterance_id)
        try:
            result = confirm.confirm(utterance_id, body.text)
        except (AlreadyConfirmedError, InvalidTransitionError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return {
            "outcome": result.outcome.value,
            "text": result.text,
            "composed_by": result.composed_by,
            "degraded": result.degraded,
            "citations": [citation.model_dump() for citation in result.citations],
        }

    @router.post("/{utterance_id}/discard")
    def discard(utterance_id: UUID) -> dict[str, Any]:
        get_or_404(utterance_id)
        try:
            return _state(confirm.discard(utterance_id))
        except InvalidTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None

    return router


def build_speech_router(*, tts: TextToSpeech) -> APIRouter:
    """`POST /api/v1/voice/speak`: the answer on screen, read aloud (WAV)."""
    router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

    @router.post("/speak")
    def speak(body: SpeakRequest) -> Response:
        if not tts.available:
            raise HTTPException(status_code=503, detail="there is no voice service")
        spoken = speakable(body.text)
        if not spoken:
            raise HTTPException(status_code=400, detail="there is nothing to read")
        try:
            audio = tts.speak(spoken)
        except (OSError, ValueError):  # the voice container does not answer or returned no audio
            raise HTTPException(
                status_code=503, detail="the voice service is not answering"
            ) from None
        if audio is None:
            raise HTTPException(status_code=503, detail="there is no voice service")
        return Response(content=audio, media_type="audio/wav")

    return router
