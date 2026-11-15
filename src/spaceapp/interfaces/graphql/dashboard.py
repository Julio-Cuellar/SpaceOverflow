"""Signos vitales de la cabina para el tablero. Función pura sobre lecturas y alertas activas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from uuid import UUID

from spaceapp.modules.monitoring.domain.physics import partial_pressure_o2
from spaceapp.modules.monitoring.domain.units import kpa_to_mmhg
from spaceapp.modules.monitoring.facade import ActiveAlertView, RuleView
from spaceapp.modules.telemetry.facade import LatestReadingView

# (clave, etiqueta) en el orden en que se muestran. `pio2` se deriva de presión y oxígeno.
VITALS: tuple[tuple[str, str], ...] = (
    ("pressure_kpa", "Presión total"),
    ("o2_pct", "Oxígeno"),
    ("co2_mmhg", "CO₂"),
    ("temperature_c", "Temperatura"),
    ("humidity_pct", "Humedad relativa"),
    ("pio2", "PIO₂ (oxígeno inspirado)"),
)
# Parámetro de una regla -> signo vital que colorea. `n2_pct` no tiene signo propio.
PARAMETER_TO_VITAL = {
    "ppco2": "co2_mmhg",
    "pio2": "pio2",
    "pressure_kpa": "pressure_kpa",
    "pressure_rate": "pressure_kpa",
    "humidity_pct": "humidity_pct",
    "temperature_c": "temperature_c",
}
SEVERITY_ORDER = {"normal": 0, "atencion": 1, "alerta": 2, "critico": 3}
EVIDENCE_ORDER = {"VERIFICADO": 0, "TB": 1, "DEMO": 2, "NO_VERIFICADO": 3}


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
    """Severidad global y signos vitales.

    Sin alerta, un signo es el promedio de las zonas y no tiene zona. Con alertas, manda la
    peor: su severidad, su zona, el valor de esa zona y la evidencia de su regla.
    """
    global_severity = _worst(a.severity for a in alerts)
    cabin = [r for r in latest if r.domain == "cabina" and r.zone_id is not None]
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
