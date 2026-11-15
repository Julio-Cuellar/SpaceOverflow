from spaceapp.modules.monitoring.application.evaluate_readings import EvaluateReadings
from spaceapp.platform.bus import EventBus

CONSUMER = "monitoring.evaluate_readings"


def register_monitoring(bus: EventBus, handler: EvaluateReadings) -> None:
    bus.subscribe("telemetry.readings_recorded", CONSUMER, handler.handle)
