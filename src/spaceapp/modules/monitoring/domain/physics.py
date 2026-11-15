"""Quantities derived from the atmosphere. Pure functions, no I/O."""

WATER_VAPOR_MMHG = 47.0  # water vapour pressure in the lungs at 37 °C


def partial_pressure_o2(p_total_mmhg: float, o2_fraction: float) -> float:
    """PIO2 = (P_total - 47 mmHg) x FO2. Oxygen is evaluated as a partial pressure."""
    if p_total_mmhg <= WATER_VAPOR_MMHG:
        raise ValueError(
            f"total pressure must exceed {WATER_VAPOR_MMHG} mmHg (water vapour): {p_total_mmhg}"
        )
    if not 0 < o2_fraction <= 1:
        raise ValueError(f"the O2 fraction must be between 0 and 1: {o2_fraction}")
    return (p_total_mmhg - WATER_VAPOR_MMHG) * o2_fraction


def co2_mmhg_to_percent(co2_mmhg: float, p_total_mmhg: float) -> float:
    """The same limit in mmHg is a different percentage at another total pressure."""
    return co2_mmhg / p_total_mmhg * 100


def co2_percent_to_mmhg(percent: float, p_total_mmhg: float) -> float:
    return percent / 100 * p_total_mmhg


def pressure_rate_psi_per_min(p_start_psi: float, p_end_psi: float, minutes: float) -> float:
    """Rate of pressure change (absolute value) in psi per minute."""
    if minutes <= 0:
        raise ValueError("the time must be positive")
    return abs(p_end_psi - p_start_psi) / minutes
