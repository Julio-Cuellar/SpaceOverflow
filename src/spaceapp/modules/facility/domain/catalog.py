"""Incident type catalog (ADR-9): category, detection, severity, zones and actions."""

from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("attention", "alert", "critical")
EVIDENCE_STATES = ("VERIFIED", "TB", "DEMO", "UNVERIFIED")
DETECTIONS = ("AUTO", "MANUAL")


class InvalidCatalog(ValueError):
    pass


@dataclass(frozen=True)
class IncidentType:
    key: str
    category: str
    name: str
    detection: str
    rule_keys: tuple[str, ...]
    default_severity: str
    evidence_state: str
    typical_zones: tuple[str, ...]
    suggested_actions: tuple[str, ...]


@dataclass(frozen=True)
class IncidentCatalog:
    version: str
    categories: dict[str, str]
    types: tuple[IncidentType, ...]
    pending_rules: frozenset[str]

    def __post_init__(self) -> None:
        seen: dict[str, str] = {}
        keys = [t.key for t in self.types]
        if len(keys) != len(set(keys)):
            raise InvalidCatalog("duplicate type keys")
        for t in self.types:
            if t.category not in self.categories:
                raise InvalidCatalog(f"{t.key}: unknown category {t.category!r}")
            if t.default_severity not in SEVERITIES:
                raise InvalidCatalog(f"{t.key}: unknown severity {t.default_severity!r}")
            if t.evidence_state not in EVIDENCE_STATES:
                raise InvalidCatalog(f"{t.key}: unknown evidence state {t.evidence_state!r}")
            if t.detection not in DETECTIONS:
                raise InvalidCatalog(f"{t.key}: unknown detection {t.detection!r}")
            if t.detection == "AUTO" and not t.rule_keys:
                raise InvalidCatalog(f"{t.key}: an AUTO type needs at least one rule")
            if t.detection == "MANUAL" and t.rule_keys:
                raise InvalidCatalog(f"{t.key}: a MANUAL type takes no rules")
            for rule in t.rule_keys:
                if rule in seen:
                    raise InvalidCatalog(f"rule {rule} is in both {seen[rule]} and {t.key}")
                seen[rule] = t.key

    def get(self, key: str) -> IncidentType | None:
        return next((t for t in self.types if t.key == key), None)

    def type_for_rule(self, rule_key: str) -> IncidentType | None:
        return next((t for t in self.types if rule_key in t.rule_keys), None)
