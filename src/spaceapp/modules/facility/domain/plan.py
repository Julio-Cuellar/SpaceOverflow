"""Habitat floor plan: zones with their geometry. It is data: changing ship means changing JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from spaceapp.platform.ids import habitat_id, zone_id


class InvalidPlan(ValueError):
    pass


@dataclass(frozen=True)
class ZonePlan:
    code: str
    name: str
    kind: str
    deck: int
    layout: dict[str, Any]


@dataclass(frozen=True)
class PlannedZone:
    id: UUID
    code: str
    name: str
    kind: str
    deck: int
    layout: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    habitat_code: str
    habitat_name: str
    habitat_kind: str
    p_total_nominal_kpa: float
    zone_plans: tuple[ZonePlan, ...]
    canvas: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        codes = [z.code for z in self.zone_plans]
        repeated = sorted({c for c in codes if codes.count(c) > 1})
        if repeated:
            raise InvalidPlan(f"duplicate zone codes: {', '.join(repeated)}")

    @property
    def habitat_id(self) -> UUID:
        return habitat_id(self.habitat_code)

    @property
    def zones(self) -> tuple[PlannedZone, ...]:
        return tuple(
            PlannedZone(
                zone_id(self.habitat_code, z.code), z.code, z.name, z.kind, z.deck, z.layout
            )
            for z in self.zone_plans
        )

    def zone(self, code: str) -> PlannedZone | None:
        return next((z for z in self.zones if z.code == code), None)

    def zone_by_id(self, zid: UUID) -> PlannedZone | None:
        return next((z for z in self.zones if z.id == zid), None)
