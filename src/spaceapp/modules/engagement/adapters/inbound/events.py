"""Missions subscriptions: incidents, recommendations and Ground plans."""

from __future__ import annotations

from spaceapp.modules.engagement.application.service import CONSUMERS, EngagementService
from spaceapp.platform.bus import EventBus


def register_engagement(bus: EventBus, service: EngagementService) -> None:
    handlers = {
        "facility.incident_opened": service.on_incident_opened,
        "facility.incident_resolved": service.on_incident_resolved,
        "knowledge.recommendation_ready": service.on_recommendation_ready,
        "groundlink.ground_plan_received": service.on_ground_plan_received,
    }
    for event_type, handler in handlers.items():
        bus.subscribe(event_type, CONSUMERS[event_type], handler)
