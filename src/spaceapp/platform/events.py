"""Event envelope and base of each module's payloads."""

from __future__ import annotations

import builtins
import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Self, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVENT_TYPE_RE = re.compile(r"^[a-z]+\.[a-z_]+$")


class EventPayload(BaseModel):
    """Base of the contracts. Each subclass declares its `event_type` (module.fact)."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    event_type: ClassVar[str]


P = TypeVar("P", bound=EventPayload)


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    type: str
    version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str
    aggregate_id: UUID
    partition_key: str
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    payload: dict[str, Any]

    @field_validator("type")
    @classmethod
    def _type_is_module_dot_fact(cls, v: str) -> str:
        if not EVENT_TYPE_RE.fullmatch(v):
            raise ValueError(f"the event type must be module.fact in snake_case: {v!r}")
        return v

    @classmethod
    def from_payload(
        cls,
        payload: EventPayload,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        partition_key: str,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> Self:
        return cls(
            type=payload.event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            partition_key=partition_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload.model_dump(mode="json"),
        )

    def payload_as(self, model: builtins.type[P]) -> P:
        if model.event_type != self.type:
            raise ValueError(f"the event is {self.type!r}, not {model.event_type!r}")
        return model.model_validate(self.payload)
