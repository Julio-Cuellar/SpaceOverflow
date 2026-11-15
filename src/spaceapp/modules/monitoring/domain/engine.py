"""Rule engine: deterministic, no I/O. The language model never decides here."""

from __future__ import annotations

import operator as op
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from spaceapp.modules.monitoring.domain.physics import (
    WATER_VAPOR_MMHG,
    co2_mmhg_to_percent,
    partial_pressure_o2,
)
from spaceapp.modules.monitoring.domain.rules import Rule
from spaceapp.modules.monitoring.domain.series import Sample, mean, within
from spaceapp.modules.monitoring.domain.trend import detect_trend
from spaceapp.modules.monitoring.domain.units import kpa_to_mmhg, kpa_to_psi

_OPS = {"<": op.lt, "<=": op.le, ">": op.gt, ">=": op.ge}
_SEV_ORDER = {"critical": 0, "alert": 1, "attention": 2}


@dataclass(frozen=True)
class RuleHit:
    rule_key: str
    zone_id: UUID | None
    parameter: str
    severity: str
    value: float
    unit: str
    operator: str
    threshold: float
    window_s: int
    band: str
    kind: str
    evidence_state: str
    source_requirement: str
    source_document: str
    hrp_hazard: str
    action_key: str

    def as_evidence(self) -> dict[str, Any]:
        """What is shown to audit the alert: value, rule, source and state."""
        return {
            "parameter": self.parameter,
            "value": round(self.value, 4),
            "unit": self.unit,
            "operator": self.operator,
            "threshold": round(self.threshold, 4),
            "window_s": self.window_s,
            "band": self.band,
            "kind": self.kind,
            "evidence_state": self.evidence_state,
            "source_requirement": self.source_requirement,
            "source_document": self.source_document,
            "hrp_hazard": self.hrp_hazard,
            "action_key": self.action_key,
        }


@dataclass(frozen=True)
class EvaluationResult:
    hits: list[RuleHit]
    superseded: frozenset[str]


def _at(series: Sequence[Sample], ts: datetime) -> float | None:
    """Last known value at `ts` (the series must be sorted)."""
    idx = bisect_right([s.ts for s in series], ts)
    return series[idx - 1].value if idx else None


def derive_series(raw: Mapping[str, Sequence[Sample]]) -> dict[str, list[Sample]]:
    """Adds the derived quantities: ppCO2, PIO2 and nitrogen percentage."""
    out = {k: sorted(v, key=lambda s: s.ts) for k, v in raw.items()}
    if "co2_mmhg" in out:
        out["ppco2"] = out["co2_mmhg"]
    pressure, o2, co2 = out.get("pressure_kpa"), out.get("o2_pct"), out.get("co2_mmhg")
    if pressure and o2:
        pio2: list[Sample] = []
        n2: list[Sample] = []
        for s in o2:
            p_kpa = _at(pressure, s.ts)
            if p_kpa is None:
                continue
            p_mmhg = kpa_to_mmhg(p_kpa)
            if p_mmhg > WATER_VAPOR_MMHG and 0 < s.value <= 100:
                pio2.append(Sample(s.ts, partial_pressure_o2(p_mmhg, s.value / 100)))
                co2_v = _at(co2, s.ts) if co2 else None
                if co2_v is not None:
                    n2.append(Sample(s.ts, 100 - s.value - co2_mmhg_to_percent(co2_v, p_mmhg)))
        out["pio2"] = pio2
        if n2:
            out["n2_pct"] = n2
    return out


def _band(rule: Rule, value: float) -> str:
    words = {"<": "below", "<=": "at or below", ">": "above", ">=": "at or above"}
    return f"{words[rule.operator]} {rule.threshold:g} {rule.unit}"


def _hit(
    rule: Rule,
    zone_id: UUID | None,
    value: float,
    band: str | None = None,
    threshold: float | None = None,
) -> RuleHit:
    return RuleHit(
        rule_key=rule.key,
        zone_id=zone_id,
        parameter=rule.parameter,
        severity=rule.severity,
        value=value,
        unit=rule.unit,
        operator=rule.operator,
        threshold=rule.threshold if threshold is None else threshold,
        window_s=rule.window_s,
        band=band or _band(rule, value),
        kind=rule.kind,
        evidence_state=rule.evidence_state,
        source_requirement=rule.source_requirement,
        source_document=rule.source_document,
        hrp_hazard=rule.hrp_hazard,
        action_key=rule.action_key,
    )


def _windowed_value(
    rule: Rule, series: Sequence[Sample], now: datetime, scale: float
) -> float | None:
    """Value to compare: the latest reading, or the window average once covered."""
    if rule.window_s == 0:
        recent = within(
            series, now - timedelta(seconds=int(rule.params.get("max_age_s", 120))), now
        )
        return recent[-1].value if recent else None
    window = rule.window_s * (scale if rule.params.get("scalable", True) else 1.0)
    samples = within(series, now - timedelta(seconds=window), now)
    if len(samples) < 2:
        return None
    span = (samples[-1].ts - samples[0].ts).total_seconds()
    if span < float(rule.params.get("min_coverage", 0.5)) * window:
        return None
    return mean(samples)


def _pressure_rate(rule: Rule, raw_pressure: Sequence[Sample], now: datetime) -> float | None:
    samples = within(raw_pressure, now - timedelta(seconds=rule.window_s), now)
    if len(samples) < 2:
        return None
    first, last = samples[0], samples[-1]
    minutes = (last.ts - first.ts).total_seconds() / 60
    if minutes <= 0:
        return None
    change = abs(kpa_to_psi(last.value) - kpa_to_psi(first.value))
    if change <= float(rule.params.get("min_change_psi", 0.0)):
        return None
    return change / minutes


def evaluate(
    zone_id: UUID | None,
    raw: Mapping[str, Sequence[Sample]],
    rules: Sequence[Rule],
    now: datetime,
    *,
    window_scale: float = 1.0,
) -> EvaluationResult:
    """Evaluates a zone. `window_scale` shortens the windows for the demo."""
    series = derive_series(raw)
    by_key = {r.key: r for r in rules}
    threshold_hits: list[RuleHit] = []
    trend_hits: list[RuleHit] = []
    for rule in rules:
        if not rule.active:
            continue
        if rule.kind == "trend":
            data = series.get(rule.parameter)
            if not data:
                continue
            res = detect_trend(
                data,
                now,
                min_delta=float(rule.params.get("min_delta", rule.threshold)),
                k=float(rule.params.get("k", 4.0)),
                baseline_from_s=int(rule.params.get("baseline_from_s", 60)),
                baseline_to_s=int(rule.params.get("baseline_to_s", 20)),
                recent_s=int(rule.params.get("recent_s", 5)),
                min_baseline_points=int(rule.params.get("min_baseline_points", 20)),
                min_recent_points=int(rule.params.get("min_recent_points", 3)),
            )
            if res is not None:
                trend_hits.append(
                    _hit(
                        rule,
                        zone_id,
                        res.recent_mean,
                        threshold=res.threshold,
                        band=f"change of {res.delta:+.2f} {rule.unit} versus the previous 40 s",
                    )
                )
            continue
        if rule.parameter == "pressure_rate":
            value = _pressure_rate(rule, series.get("pressure_kpa", []), now)
        else:
            data = series.get(rule.parameter)
            value = _windowed_value(rule, data, now, window_scale) if data else None
        if value is not None and _OPS[rule.operator](value, rule.threshold):
            threshold_hits.append(_hit(rule, zone_id, value))
    covered = {h.parameter for h in threshold_hits}
    hits = threshold_hits + [h for h in trend_hits if h.parameter not in covered]
    superseded = frozenset(s for h in hits for s in by_key[h.rule_key].supersedes)
    final = [h for h in hits if h.rule_key not in superseded]
    final.sort(key=lambda h: (_SEV_ORDER[h.severity], h.rule_key))
    return EvaluationResult(hits=final, superseded=superseded)
