"""Knowledge subscription to the bus: each `monitoring.alert_raised` produces a recommendation."""

from __future__ import annotations

from spaceapp.modules.knowledge.application.handle_alert_raised import CONSUMER, HandleAlertRaised
from spaceapp.platform.bus import EventBus

__all__ = ["CONSUMER", "register_knowledge"]


def register_knowledge(bus: EventBus, handler: HandleAlertRaised) -> None:
    bus.subscribe("monitoring.alert_raised", CONSUMER, handler.handle)
