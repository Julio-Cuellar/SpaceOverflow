"""REST tools of the n8n agent (plan: RAG is a tool of the agent).

Read-only and only during an open turn: the turn identifier goes in the path and the
`RetrievalLog` rejects one that does not exist, already ended or was cut by timeout. Nothing here
can change an alert. What the search returns is recorded: the citations of the answer come from it.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from spaceapp.modules.assistant.application.ask import source_label
from spaceapp.modules.assistant.application.retrieval_log import (
    RetrievalLog,
    TurnClosedError,
    passage_id,
)
from spaceapp.modules.assistant.ports import ActiveAlerts, PassageSearch

DEFAULT_K = 3
MAX_K = 5
NO_PASSAGES = "There are no passages that support this question."


class SearchRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    k: int = Field(default=DEFAULT_K, ge=1, le=MAX_K)


class PassageView(BaseModel):
    passage_id: str
    text: str
    source: str


class SearchResponse(BaseModel):
    passages: list[PassageView]
    message: str | None = None


class AlertsResponse(BaseModel):
    alerts: list[str]


def build_router(*, log: RetrievalLog, passages: PassageSearch, alerts: ActiveAlerts) -> APIRouter:
    router = APIRouter(prefix="/api/v1/assistant/tools", tags=["assistant-tools"])

    def require_open(turn_id: UUID) -> None:
        if not log.is_open(turn_id):
            raise HTTPException(status_code=404, detail="the turn is not open")

    @router.post("/{turn_id}/search_passages", response_model=SearchResponse)
    def search_passages(turn_id: UUID, request: SearchRequest) -> SearchResponse:
        require_open(turn_id)
        found = passages.search(request.query, request.k)
        if not found:
            return SearchResponse(passages=[], message=NO_PASSAGES)
        try:
            log.record(turn_id, found)
        except TurnClosedError:
            raise HTTPException(status_code=404, detail="the turn is not open") from None
        return SearchResponse(
            passages=[
                PassageView(
                    passage_id=passage_id(citation),
                    text=citation.excerpt,
                    source=source_label(citation),
                )
                for citation in found
            ]
        )

    @router.get("/{turn_id}/active_alerts", response_model=AlertsResponse)
    def active_alerts(turn_id: UUID) -> AlertsResponse:
        require_open(turn_id)
        return AlertsResponse(alerts=alerts.titles())

    return router
