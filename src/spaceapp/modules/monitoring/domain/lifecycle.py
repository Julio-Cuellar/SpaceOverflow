"""Alert lifecycle: raise, keep, resolve with hysteresis and acknowledge."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from spaceapp.modules.monitoring.domain.engine import RuleHit


@dataclass(frozen=True)
class ActiveAlert:
    id: UUID
    rule_key: str
    zone_id: UUID | None
    severity: str
    status: str  # raised | acknowledged
    clear_streak: int = 0


@dataclass(frozen=True)
class AlertRecord:
    id: UUID
    habitat_id: UUID
    zone_id: UUID | None
    status: str  # raised | acknowledged | resolved


@dataclass
class Decision:
    raise_hits: list[RuleHit] = field(default_factory=list)
    keep: list[tuple[ActiveAlert, RuleHit]] = field(default_factory=list)
    clearing: list[tuple[ActiveAlert, int]] = field(default_factory=list)
    resolve: list[ActiveAlert] = field(default_factory=list)


def reconcile(
    active: Sequence[ActiveAlert],
    hits: Sequence[RuleHit],
    *,
    superseded: Collection[str],
    hysteresis: int,
) -> Decision:
    """Compares a zone's active alerts with what was just evaluated.

    - A hit with no active alert raises one (deduplicated by rule and zone).
    - A hit with an active alert keeps it and resets the clean-evaluation count.
    - With no hit, the alert resolves after `hysteresis` consecutive clean evaluations.
    - A rule superseded by a more severe one resolves immediately.
    """
    hit_by = {(h.rule_key, h.zone_id): h for h in hits}
    active_keys = {(a.rule_key, a.zone_id) for a in active}
    decision = Decision(raise_hits=[h for k, h in hit_by.items() if k not in active_keys])
    for a in active:
        key = (a.rule_key, a.zone_id)
        if key in hit_by:
            decision.keep.append((a, hit_by[key]))
        elif a.rule_key in superseded:
            decision.resolve.append(a)
        else:
            streak = a.clear_streak + 1
            if streak >= hysteresis:
                decision.resolve.append(a)
            else:
                decision.clearing.append((a, streak))
    return decision


def ack_decision(status: str) -> Literal["acknowledge", "already", "resolved"]:
    if status == "resolved":
        return "resolved"
    if status == "acknowledged":
        return "already"
    return "acknowledge"
