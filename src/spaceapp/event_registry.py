"""Registro de todos los eventos del sistema. Lo usan el relay, el gateway y las pruebas."""

from __future__ import annotations

from collections.abc import Mapping

from spaceapp.modules.assistant.contracts import EVENTS as ASSISTANT
from spaceapp.modules.crew.contracts import EVENTS as CREW
from spaceapp.modules.engagement.contracts import EVENTS as ENGAGEMENT
from spaceapp.modules.facility.contracts import EVENTS as FACILITY
from spaceapp.modules.groundlink.contracts import EVENTS as GROUNDLINK
from spaceapp.modules.knowledge.contracts import EVENTS as KNOWLEDGE
from spaceapp.modules.monitoring.contracts import EVENTS as MONITORING
from spaceapp.modules.telemetry.contracts import EVENTS as TELEMETRY
from spaceapp.platform.events import EventPayload


def _merge(*parts: Mapping[str, type[EventPayload]]) -> dict[str, type[EventPayload]]:
    merged: dict[str, type[EventPayload]] = {}
    for part in parts:
        for name, model in part.items():
            if name in merged:
                raise ValueError(f"evento duplicado: {name}")
            merged[name] = model
    return merged


EVENT_MODELS = _merge(
    TELEMETRY, MONITORING, KNOWLEDGE, ASSISTANT, CREW, FACILITY, ENGAGEMENT, GROUNDLINK
)
