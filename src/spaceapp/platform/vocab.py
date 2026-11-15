"""Vocabulary shared between modules (shared kernel)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["attention", "alert", "critical"]
EvidenceState = Literal["VERIFIED", "TB", "DEMO", "UNVERIFIED"]


class Citation(BaseModel):
    """Citation of a source. Every recommendation or answer carries one."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_code: str
    requirement_ref: str | None = None
    page: int | None = None
    excerpt: str
    evidence_state: EvidenceState
