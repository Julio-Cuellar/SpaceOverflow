from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from spaceapp.modules.telemetry.domain.simulator import ZoneBaseline
from spaceapp.platform.ids import habitat_id, zone_id


@dataclass(frozen=True)
class Layout:
    """Zones that are simulated. The codes match those of the Facility floor plan."""

    habitat_code: str
    zones: tuple[ZoneBaseline, ...]

    @property
    def habitat_id(self) -> UUID:
        return habitat_id(self.habitat_code)

    def zone_id(self, code: str) -> UUID:
        return zone_id(self.habitat_code, code)
