"""Facility subscription to Monitoring alerts."""

from __future__ import annotations

from spaceapp.modules.facility.application.service import (
    CONSUMER_RAISED,
    CONSUMER_RESOLVED,
    FacilityService,
)
from spaceapp.platform.bus import EventBus


def register_facility(bus: EventBus, service: FacilityService) -> None:
    bus.subscribe("monitoring.alert_raised", CONSUMER_RAISED, service.on_alert_raised)
    bus.subscribe("monitoring.alert_resolved", CONSUMER_RESOLVED, service.on_alert_resolved)
