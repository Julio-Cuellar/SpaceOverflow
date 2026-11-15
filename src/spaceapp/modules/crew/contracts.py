"""Public events of Crew."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from spaceapp.platform.events import EventPayload


class BaselineUpdated(EventPayload):
    event_type: ClassVar[str] = "crew.baseline_updated"
    crew_member_id: UUID
    metric: str
    value: float


class ConsentChanged(EventPayload):
    event_type: ClassVar[str] = "crew.consent_changed"
    crew_member_id: UUID
    category: str
    shared: bool


EVENTS = {m.event_type: m for m in (BaselineUpdated, ConsentChanged)}
