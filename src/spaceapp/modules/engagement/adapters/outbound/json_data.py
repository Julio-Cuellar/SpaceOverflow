"""System templates (daily health and maintenance routines) from `data/engagement/`."""

from __future__ import annotations

import json
from pathlib import Path

from spaceapp.modules.engagement.domain.tasks import Template
from spaceapp.platform.ids import stable_uuid


def load_system_templates(path: Path | str) -> list[Template]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Template(
            id=stable_uuid("template", t["key"]),
            kind=t["kind"],
            title=t["title"],
            recurrence=t["recurrence"],
            zone_code=t["zone_code"],
            origin="SYSTEM",
            active=True,
            due_time=t["due_time"],
        )
        for t in raw["templates"]
    ]
