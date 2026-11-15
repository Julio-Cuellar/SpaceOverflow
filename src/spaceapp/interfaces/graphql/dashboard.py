"""Cabin vital signs for the dashboard. Pure function over readings and active alerts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from uuid import UUID

from spaceapp.modules.monitoring.domain.physics import partial_pressure_o2
from spaceapp.modules.monitoring.domain.units import kpa_to_mmhg
from spaceapp.modules.monitoring.facade import ActiveAlertView, RuleView
from spaceapp.modules.telemetry.facade import LatestReadingView

# (key, label) in display order. `pio2` is derived from pressure and oxygen.
VITALS: tuple[tuple[str, str], ...] = (
    ("pressure_kpa", "Total pressure"),
    ("o2_pct", "Oxygen"),
    ("co2_mmhg", "CO₂"),
    ("temperature_c", "Temperature"),
    ("humidity_pct", "Relative humidity"),
    ("pio2", "PIO₂ (inspired oxygen)"),
)
# Rule parameter -> vital sign it colours. `n2_pct` has no vital sign of its own.
PARAMETER_TO_VITAL = {
    "ppco2": "co2_mmhg",
    "pio2": "pio2",
    "pressure_kpa": "pressure_kpa",
    "pressure_rate": "pressure_kpa",
    "humidity_pct": "humidity_pct",
    "temperature_c": "temperature_c",
}
SEVERITY_ORDER = {"normal": 0, "attention": 1, "alert": 2, "critical": 3}
EVIDENCE_ORDER = {"VERIFIED": 0, "TB": 1, "DEMO": 2, "UNVERIFIED": 3}


@dataclass(frozen=True)
class VitalData:
    key: str
    label: str
    value: float
    unit: str
    domain: str
    severity: str
    evidence_state: str
    origin: str
    zone_id: UUID | None


def _worst(severities: Iterable[str]) -> str:
    return max(severities, key=SEVERITY_ORDER.__getitem__, default="normal")


def _pio2(pressure_kpa: float, o2_pct: float) -> float:
    return partial_pressure_o2(kpa_to_mmhg(pressure_kpa), o2_pct / 100)


def build_dashboard(
    latest: Sequence[LatestReadingView],
    alerts: Sequence[ActiveAlertView],
    rules: Mapping[str, RuleView],
) -> tuple[str, list[VitalData]]:
    """Global severity and vital signs.

    With no alert, a vital sign is the average across zones and has no zone. With alerts,
    the worst one rules: its severity, its zone, that zone's value and its rule's evidence.
    """
    global_severity = _worst(a.severity for a in alerts)
    cabin = [r for r in latest if r.domain == "cabin" and r.zone_id is not None]
    if not cabin:
        return global_severity, []

    by_metric: dict[str, dict[UUID, LatestReadingView]] = {}
    for r in cabin:
        by_metric.setdefault(r.metric, {})[r.zone_id] = r  # type: ignore[index]
    pressure, o2 = by_metric.get("pressure_kpa", {}), by_metric.get("o2_pct", {})

    def zone_value(key: str, zone: UUID) -> float | None:
        if key == "pio2":
            if zone in pressure and zone in o2:
                return _pio2(pressure[zone].value, o2[zone].value)
            return None
        reading = by_metric.get(key, {}).get(zone)
        return reading.value if reading else None

    def evidence_of_rules(key: str) -> str:
        states = [
            r.evidence_state for r in rules.values() if PARAMETER_TO_VITAL.get(r.parameter) == key
        ]
        return min(states, key=EVIDENCE_ORDER.__getitem__, default="DEMO")

    vitals: list[VitalData] = []
    for key, label in VITALS:
        sources = by_metric.get(key) if key != "pio2" else pressure
        if not sources or (key == "pio2" and not o2):
            continue
        sample = next(iter(sources.values()))
        unit = "mmHg" if key == "pio2" else sample.unit
        own = [
            a
            for a in alerts
            if (rule := rules.get(a.rule_key)) and PARAMETER_TO_VITAL.get(rule.parameter) == key
        ]
        worst = max(own, key=lambda a: SEVERITY_ORDER[a.severity], default=None)
        value = zone_value(key, worst.zone_id) if worst and worst.zone_id else None
        if worst is not None and value is not None:
            vitals.append(
                VitalData(
                    key,
                    label,
                    value,
                    unit,
                    sample.domain,
                    worst.severity,
                    worst.evidence_state,
                    sample.origin,
                    worst.zone_id,
                )
            )
            continue
        values = [v for z in sources if (v := zone_value(key, z)) is not None]
        vitals.append(
            VitalData(
                key,
                label,
                fmean(values),
                unit,
                sample.domain,
                worst.severity if worst else "normal",
                worst.evidence_state if worst else evidence_of_rules(key),
                sample.origin,
                None,
            )
        )
    return global_severity, vitals
