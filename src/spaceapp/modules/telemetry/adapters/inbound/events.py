from spaceapp.modules.telemetry.application.rollup import RecomputeRollup
from spaceapp.platform.bus import EventBus

CONSUMER = "telemetry.rollup"


def register_telemetry(bus: EventBus, handler: RecomputeRollup) -> None:
    bus.subscribe("telemetry.readings_recorded", CONSUMER, handler.handle)
