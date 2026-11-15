"""Reglas del catálogo. Cada regla lleva su fuente y su estado de evidencia."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

SEVERITIES = ("atencion", "alerta", "critico")
EVIDENCE_STATES = ("VERIFICADO", "TB", "DEMO")
OPERATORS = ("<", "<=", ">", ">=")
KINDS = ("umbral", "tendencia")


class InvalidRule(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    key: str
    kind: str
    parameter: str
    operator: str
    threshold: float
    unit: str
    window_s: int
    severity: str
    source_requirement: str
    source_document: str
    evidence_state: str
    hrp_hazard: str
    action_key: str
    active: bool = True
    params: Mapping[str, Any] = field(default_factory=dict)
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise InvalidRule("la regla necesita una clave")
        if self.kind not in KINDS:
            raise InvalidRule(f"{self.key}: tipo desconocido {self.kind!r}")
        if self.operator not in OPERATORS:
            raise InvalidRule(f"{self.key}: operador desconocido {self.operator!r}")
        if self.severity not in SEVERITIES:
            raise InvalidRule(f"{self.key}: severidad desconocida {self.severity!r}")
        if self.evidence_state not in EVIDENCE_STATES:
            raise InvalidRule(
                f"{self.key}: estado de evidencia desconocido {self.evidence_state!r}"
            )
        if not self.source_requirement.strip() or not self.source_document.strip():
            raise InvalidRule(f"{self.key}: toda regla necesita requisito y documento de origen")
        if self.window_s < 0:
            raise InvalidRule(f"{self.key}: la ventana no puede ser negativa")
        if self.kind == "tendencia" and self.evidence_state != "DEMO":
            raise InvalidRule(f"{self.key}: una regla de tendencia solo puede ser DEMO")


@dataclass(frozen=True)
class RuleCatalog:
    version: str
    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        keys = [r.key for r in self.rules]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            raise InvalidRule(f"claves duplicadas en el catálogo: {', '.join(dup)}")
        known = set(keys)
        for r in self.rules:
            missing = set(r.supersedes) - known
            if missing:
                raise InvalidRule(
                    f"{r.key}: supersedes apunta a reglas inexistentes: {sorted(missing)}"
                )

    def by_key(self) -> dict[str, Rule]:
        return {r.key: r for r in self.rules}

    def active_rules(self) -> tuple[Rule, ...]:
        return tuple(r for r in self.rules if r.active)
