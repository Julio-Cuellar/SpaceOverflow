"""Simulador de zonas de la nave. Determinista para una semilla; origen siempre SIMULATED."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

# (métrica, unidad, periodo de muestreo en s) según V2 6001, Tabla 6.1-1:
# atmósfera cada 5 s, presión cada 1 s, temperatura y humedad cada 1 min.
SENSOR_SPECS: tuple[tuple[str, str, int], ...] = (
    ("pressure_kpa", "kPa", 1),
    ("o2_pct", "%", 5),
    ("co2_mmhg", "mmHg", 5),
    ("temperature_c", "°C", 60),
    ("humidity_pct", "%", 60),
)
NOISE = {
    "pressure_kpa": 0.04,
    "o2_pct": 0.04,
    "co2_mmhg": 0.03,
    "temperature_c": 0.06,
    "humidity_pct": 0.3,
}
NOMINAL = {"pressure_kpa": 101.3, "o2_pct": 21.0}
# escenario -> (metas por métrica, tasa de aproximación por segundo)
SCENARIOS: dict[str, tuple[dict[str, float], float]] = {
    "co2_slow": ({"co2_mmhg": 3.6}, 0.1),
    "pressure_leak": ({"pressure_kpa": 55.0}, 0.05),
    "humidity_high": ({"humidity_pct": 82.0}, 0.1),
    "o2_failure": ({"o2_pct": 17.5}, 0.1),
    "heat": ({"temperature_c": 29.5}, 0.1),
}
RETURN_RATE = 0.1


class UnknownScenario(LookupError):
    pass


class UnknownZone(LookupError):
    pass


@dataclass(frozen=True)
class ZoneBaseline:
    code: str
    temperature_c: float
    humidity_pct: float
    co2_mmhg: float

    def base(self) -> dict[str, float]:
        return {
            **NOMINAL,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "co2_mmhg": self.co2_mmhg,
        }


@dataclass(frozen=True)
class SimReading:
    zone_code: str
    metric: str
    ts: datetime
    value: float


@dataclass
class _Zone:
    baseline: ZoneBaseline
    rng: random.Random
    values: dict[str, float]
    scenarios: dict[str, float] = field(default_factory=dict)  # clave -> velocidad


class Simulator:
    def __init__(self, zones: Sequence[ZoneBaseline], *, seed: int = 7, noise: bool = True) -> None:
        self._zones = {z.code: _Zone(z, random.Random(f"{seed}:{z.code}"), z.base()) for z in zones}
        self._noise = noise
        self._last_tick: datetime | None = None
        self._last_emit: dict[tuple[str, str], datetime] = {}

    # --- control de escenarios -------------------------------------------------------------
    def start(self, key: str, zone: str | None, *, speed: float = 1.0) -> None:
        if key == "normal":
            for z in self._zones.values():
                z.scenarios.clear()
            return
        if key not in SCENARIOS:
            raise UnknownScenario(key)
        if zone is None:
            raise ValueError("este escenario necesita una zona")
        if zone not in self._zones:
            raise UnknownZone(zone)
        self._zones[zone].scenarios[key] = speed

    def stop(self, key: str, zone: str | None) -> None:
        if zone is not None and zone not in self._zones:
            raise UnknownZone(zone)
        for code, z in self._zones.items():
            if zone in (None, code):
                z.scenarios.pop(key, None)

    def active(self) -> dict[str, dict[str, float]]:
        return {c: dict(z.scenarios) for c, z in self._zones.items() if z.scenarios}

    # --- avance del tiempo -------------------------------------------------------------------
    def _targets(self, zone: _Zone) -> dict[str, tuple[float, float]]:
        out = {m: (v, RETURN_RATE) for m, v in zone.baseline.base().items()}
        for key, speed in zone.scenarios.items():
            goals, rate = SCENARIOS[key]
            for metric, goal in goals.items():
                out[metric] = (goal, rate * speed)
        return out

    def _advance(self, dt: float) -> None:
        if dt <= 0:
            return
        for z in self._zones.values():
            for metric, (goal, rate) in self._targets(z).items():
                # Aproximación exponencial exacta: no depende del tamaño del paso.
                z.values[metric] += (goal - z.values[metric]) * (1 - math.exp(-rate * dt))

    def tick(self, now: datetime) -> list[SimReading]:
        """Avanza hasta `now` y devuelve las lecturas cuyo periodo de muestreo venció."""
        if self._last_tick is not None:
            self._advance((now - self._last_tick).total_seconds())
        self._last_tick = now
        out: list[SimReading] = []
        for code, z in self._zones.items():
            for metric, _unit, period in SENSOR_SPECS:
                last = self._last_emit.get((code, metric))
                if last is not None and (now - last).total_seconds() < period:
                    continue
                self._last_emit[(code, metric)] = now
                value = z.values[metric]
                if self._noise:
                    value += z.rng.gauss(0, NOISE[metric])
                out.append(SimReading(code, metric, now, _clamp(metric, value)))
        return out


def _clamp(metric: str, value: float) -> float:
    if metric == "co2_mmhg":
        return max(0.05, value)
    if metric in ("humidity_pct", "o2_pct"):
        return min(100.0, max(0.0, value))
    return value
