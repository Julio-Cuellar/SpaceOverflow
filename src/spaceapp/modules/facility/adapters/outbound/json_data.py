"""Carga el plano y el catálogo de tipos desde `data/facility/`."""

from __future__ import annotations

import json
from pathlib import Path

from spaceapp.modules.facility.domain.catalog import IncidentCatalog, IncidentType
from spaceapp.modules.facility.domain.plan import Plan, ZonePlan


def load_plan(path: Path | str) -> Plan:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    h = raw["habitat"]
    zones = tuple(
        ZonePlan(z["code"], z["name"], z["kind"], int(z["deck"]), dict(z["layout"]))
        for z in raw["zones"]
    )
    return Plan(
        h["code"], h["name"], h["kind"], float(h["p_total_nominal_kpa"]), zones, raw.get("canvas")
    )


def load_catalog(path: Path | str) -> IncidentCatalog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    types = tuple(
        IncidentType(
            key=t["key"],
            category=t["category"],
            name=t["name"],
            detection=t["detection"],
            rule_keys=tuple(t["rule_keys"]),
            default_severity=t["default_severity"],
            evidence_state=t["evidence_state"],
            typical_zones=tuple(t["typical_zones"]),
            suggested_actions=tuple(t["suggested_actions"]),
        )
        for t in raw["types"]
    )
    categories = {c["key"]: c["name"] for c in raw["categories"]}
    return IncidentCatalog(raw["version"], categories, types, frozenset(raw["pending_rules"]))
