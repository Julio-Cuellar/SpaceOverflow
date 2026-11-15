"""Vocabulario compartido entre módulos (kernel compartido)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["atencion", "alerta", "critico"]
EvidenceState = Literal["VERIFICADO", "TB", "DEMO", "NO_VERIFICADO"]


class Citation(BaseModel):
    """Cita de una fuente. Toda recomendación o respuesta la lleva."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_code: str
    requirement_ref: str | None = None
    page: int | None = None
    excerpt: str
    evidence_state: EvidenceState
