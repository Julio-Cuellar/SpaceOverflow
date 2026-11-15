"""Crew ports."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from spaceapp.modules.crew.domain.members import CrewMember


class CrewRepository(Protocol):
    async def upsert(self, members: Sequence[CrewMember]) -> None: ...
