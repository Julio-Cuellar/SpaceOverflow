"""Catálogo de tipos de incidencia (ADR-9): categoría, detección, severidad, zonas y acciones."""

from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("atencion", "alerta", "critico")
EVIDENCE_STATES = ("VERIFICADO", "TB", "DEMO", "NO_VERIFICADO")
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
            raise InvalidCatalog("claves de tipo repetidas")
        for t in self.types:
            if t.category not in self.categories:
                raise InvalidCatalog(f"{t.key}: categoría desconocida {t.category!r}")
            if t.default_severity not in SEVERITIES:
                raise InvalidCatalog(f"{t.key}: severidad desconocida {t.default_severity!r}")
            if t.evidence_state not in EVIDENCE_STATES:
                raise InvalidCatalog(
                    f"{t.key}: estado de evidencia desconocido {t.evidence_state!r}"
                )
            if t.detection not in DETECTIONS:
                raise InvalidCatalog(f"{t.key}: detección desconocida {t.detection!r}")
            if t.detection == "AUTO" and not t.rule_keys:
                raise InvalidCatalog(f"{t.key}: un tipo AUTO necesita al menos una regla")
            if t.detection == "MANUAL" and t.rule_keys:
                raise InvalidCatalog(f"{t.key}: un tipo MANUAL no lleva reglas")
            for rule in t.rule_keys:
                if rule in seen:
                    raise InvalidCatalog(f"la regla {rule} está en {seen[rule]} y en {t.key}")
                seen[rule] = t.key

    def get(self, key: str) -> IncidentType | None:
        return next((t for t in self.types if t.key == key), None)

    def type_for_rule(self, rule_key: str) -> IncidentType | None:
        return next((t for t in self.types if rule_key in t.rule_keys), None)
