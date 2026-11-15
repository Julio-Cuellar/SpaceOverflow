"""Crew members of a habitat: who they are, not what their body measures."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from spaceapp.platform.ids import habitat_id, stable_uuid

PORTRAITS = (1, 2, 3, 4)


def crew_member_id(habitat_code: str, code: str) -> UUID:
    return stable_uuid("crew-member", habitat_code, code)


@dataclass(frozen=True)
class CrewMember:
    id: UUID
    habitat_id: UUID
    code: str
    name: str
    role: str
    # Position in the illustrative portrait atlas of the interface (1 to 4).
    portrait: int

    @classmethod
    def create(cls, *, habitat: str, code: str, name: str, role: str, portrait: int) -> CrewMember:
        for field, value in (("code", code), ("name", name), ("role", role)):
            if not value.strip():
                raise ValueError(f"the {field} cannot be blank")
        if portrait not in PORTRAITS:
            raise ValueError(f"the portrait must be one of {PORTRAITS}, not {portrait}")
        return cls(
            crew_member_id(habitat, code),
            habitat_id(habitat),
            code.strip(),
            name.strip(),
            role.strip(),
            portrait,
        )
