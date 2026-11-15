"""Loads the crew roster from `data/crew/roster.json`."""

from __future__ import annotations

import json
from pathlib import Path

from spaceapp.modules.crew.domain.members import CrewMember


def load_roster(path: Path | str) -> list[CrewMember]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    habitat = raw["habitat_code"]
    return [
        CrewMember.create(
            habitat=habitat,
            code=m["code"],
            name=m["name"],
            role=m["role"],
            portrait=int(m["portrait"]),
        )
        for m in raw["members"]
    ]
