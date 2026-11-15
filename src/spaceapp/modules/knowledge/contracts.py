"""Eventos y DTO públicos de Conocimiento (dueño: Dev B). Es lo único, junto a la fachada, que otros módulos importan."""

from __future__ import annotations

from typing import Any, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation

# Misma cita que usa toda la plataforma. El nombre CitationDTO se conserva para el código de Dev B.
CitationDTO = Citation

SeverityName = Literal["NORMAL", "ATENCION", "ALERTA", "CRITICO"]
CauseHint = Literal["AMBIENTE", "CUERPO", "INDETERMINADO"]


class AlertRaised(BaseModel):
    """Copia local del payload de `monitoring.alert_raised`, para no importar Monitoreo."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    alert_id: UUID
    zone_id: UUID | None = None
    rule_key: str
    severity: SeverityName
    evidence: dict[str, Any]
    cause_hint: CauseHint


class RecommendationReady(EventPayload):
    event_type: ClassVar[str] = "knowledge.recommendation_ready"
    alert_id: UUID
    recommendation_id: UUID
    action_keys: list[str]
    citations: list[Citation]


class RecommendationEnriched(EventPayload):
    event_type: ClassVar[str] = "knowledge.recommendation_enriched"
    recommendation_id: UUID
    text: str


EVENTS = {m.event_type: m for m in (RecommendationReady, RecommendationEnriched)}
