"""Suscripciones del Enlace con Tierra: confirmar planes aplicados (nave) y recibirlos (Tierra)."""

from __future__ import annotations

from spaceapp.modules.groundlink.application.ground import CONSUMER_ACK, GroundControl
from spaceapp.modules.groundlink.application.receiver import CONSUMER_APPLIED, PlanReceiver
from spaceapp.platform.bus import EventBus


def register_groundlink(bus: EventBus, receiver: PlanReceiver, ground: GroundControl) -> None:
    bus.subscribe("engagement.ground_plan_applied", CONSUMER_APPLIED, receiver.on_plan_applied)
    bus.subscribe("groundlink.batch_acknowledged", CONSUMER_ACK, ground.on_batch_acknowledged)
