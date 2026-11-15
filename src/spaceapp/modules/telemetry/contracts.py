"""Public Telemetry events."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from spaceapp.platform.events import EventPayload


class LatestReading(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sensor_id: UUID
    zone_id: UUID | None = None
    metric: str
    value: float


class ReadingsRecorded(EventPayload):
    event_type: ClassVar[str] = "telemetry.readings_recorded"
    batch_id: UUID
    habitat_id: UUID
    ts_from: datetime
    ts_to: datetime
    latest: list[LatestReading]


class ScenarioChanged(EventPayload):
    event_type: ClassVar[str] = "telemetry.scenario_changed"
    key: str
    state: Literal["started", "stopped"]
    speed: float = 1.0
    zone_id: UUID | None = None


EVENTS = {m.event_type: m for m in (ReadingsRecorded, ScenarioChanged)}
