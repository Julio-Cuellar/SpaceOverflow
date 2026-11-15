"""Catalog rules. Each rule carries its source and its evidence state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

SEVERITIES = ("attention", "alert", "critical")
EVIDENCE_STATES = ("VERIFIED", "TB", "DEMO")
OPERATORS = ("<", "<=", ">", ">=")
KINDS = ("threshold", "trend")


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
            raise InvalidRule("the rule needs a key")
        if self.kind not in KINDS:
            raise InvalidRule(f"{self.key}: unknown kind {self.kind!r}")
        if self.operator not in OPERATORS:
            raise InvalidRule(f"{self.key}: unknown operator {self.operator!r}")
        if self.severity not in SEVERITIES:
            raise InvalidRule(f"{self.key}: unknown severity {self.severity!r}")
        if self.evidence_state not in EVIDENCE_STATES:
            raise InvalidRule(f"{self.key}: unknown evidence state {self.evidence_state!r}")
        if not self.source_requirement.strip() or not self.source_document.strip():
            raise InvalidRule(f"{self.key}: every rule needs a requirement and a source document")
        if self.window_s < 0:
            raise InvalidRule(f"{self.key}: the window cannot be negative")
        if self.kind == "trend" and self.evidence_state != "DEMO":
            raise InvalidRule(f"{self.key}: a trend rule can only be DEMO")


@dataclass(frozen=True)
class RuleCatalog:
    version: str
    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        keys = [r.key for r in self.rules]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            raise InvalidRule(f"duplicate keys in the catalog: {', '.join(dup)}")
        known = set(keys)
        for r in self.rules:
            missing = set(r.supersedes) - known
            if missing:
                raise InvalidRule(
                    f"{r.key}: supersedes points to nonexistent rules: {sorted(missing)}"
                )

    def by_key(self) -> dict[str, Rule]:
        return {r.key: r for r in self.rules}

    def active_rules(self) -> tuple[Rule, ...]:
        return tuple(r for r in self.rules if r.active)
