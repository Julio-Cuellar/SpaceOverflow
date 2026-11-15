"""Rutas REST de la voz: audio crudo dentro, texto editable fuera, y nada se pregunta sin confirmar.

    POST /api/v1/voice/utterances?conversation_id=…   cuerpo = audio  → 202 y el `utterance_id`
    GET  /api/v1/voice/utterances/{id}                estado y transcripción editable
    POST /api/v1/voice/utterances/{id}/confirm        {"text": …} → la respuesta del asistente
    POST /api/v1/voice/utterances/{id}/discard        descarta sin preguntar

El audio va como cuerpo crudo (no `multipart`): no hace falta una dependencia más. La transcripción
corre aparte, después de responder 202; el cliente consulta el estado hasta `TRANSCRIBED`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from spaceapp.modules.assistant.application.voice import (
    AlreadyConfirmedError,
    ConfirmUtterance,
    SubmitAudio,
    UnknownUtteranceError,
    UnsupportedAudioError,
)
from spaceapp.modules.assistant.domain.voice import InvalidTransitionError, Utterance
from spaceapp.modules.assistant.ports import UtteranceRepository


class ConfirmRequest(BaseModel):
    text: str


def _state(utterance: Utterance) -> dict[str, Any]:
    return {
        "utterance_id": str(utterance.id),
        "status": utterance.status.value,
        "text": utterance.text,
        "confidence": utterance.confidence,
        "reason": utterance.reason,
    }


def build_voice_router(
    *, submit: SubmitAudio, confirm: ConfirmUtterance, utterances: UtteranceRepository
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/voice/utterances", tags=["voice"])

    def get_or_404(utterance_id: UUID) -> Utterance:
        try:
            return utterances.get(utterance_id)
        except UnknownUtteranceError:
            raise HTTPException(status_code=404, detail="intervención desconocida") from None

    @router.post("", status_code=202)
    async def upload(
        request: Request, conversation_id: UUID, background: BackgroundTasks
    ) -> dict[str, str]:
        audio = await request.body()
        if not audio:
            raise HTTPException(status_code=400, detail="el audio está vacío")
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
