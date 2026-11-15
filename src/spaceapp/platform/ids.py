"""Identificadores estables: el mismo nombre da siempre el mismo UUID.

Así Telemetría (que simula zonas) y Nave (dueña del plano) coinciden sin importarse.
"""

from uuid import UUID, uuid5

NAMESPACE = UUID("8d0b0e5a-4f1c-4a6e-9a39-2f6f7e1c5d11")
DEFAULT_HABITAT_CODE = "nave-transito"


def stable_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE, "/".join(parts))


def habitat_id(code: str = DEFAULT_HABITAT_CODE) -> UUID:
    return stable_uuid("habitat", code)


def zone_id(habitat_code: str, zone_code: str) -> UUID:
    return stable_uuid("zone", habitat_code, zone_code)


def sensor_id(zone: UUID, metric: str) -> UUID:
    return stable_uuid("sensor", str(zone), metric)
