"""Eventos y DTO públicos del módulo knowledge. Es lo único que otros módulos pueden importar."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

EvidenceStateName = Literal["VERIFICADO", "TB", "DEMO", "NO_VERIFICADO"]
SeverityName = Literal["NORMAL", "ATENCION", "ALERTA", "CRITICO"]
CauseHint = Literal["AMBIENTE", "CUERPO", "INDETERMINADO"]


class AlertRaised(BaseModel):
    """Payload de `monitoring.alert_raised` (lo publica Monitoreo, dev A)."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    alert_id: UUID
    zone_id: UUID | None = None
    rule_key: str
    severity: SeverityName
    evidence: dict[str, Any]
    cause_hint: CauseHint


class CitationDTO(BaseModel):
    document_code: str
    requirement_ref: str | None = None
    page: int | None = None
    excerpt: str
    evidence_state: EvidenceStateName


class RecommendationReady(BaseModel):
    """Payload de `knowledge.recommendation_ready`, tal como lo define el plan (sección 4.1)."""

    alert_id: UUID
    recommendation_id: UUID
    action_keys: list[str]
    citations: list[CitationDTO]


# Provisional de la fusión: el registro de eventos de Dev A espera EVENTS. La fase 2 lo sustituye
# por los payloads reales (EventPayload) y esta prueba de contratos pasa a verde.
EVENTS: dict[str, type] = {}
