"""Magnitudes derivadas de la atmósfera. Funciones puras, sin E/S."""

WATER_VAPOR_MMHG = 47.0  # presión de vapor de agua en los pulmones a 37 °C


def partial_pressure_o2(p_total_mmhg: float, o2_fraction: float) -> float:
    """PIO2 = (P_total - 47 mmHg) x FO2. El oxígeno se evalúa como presión parcial."""
    if p_total_mmhg <= WATER_VAPOR_MMHG:
        raise ValueError(
            f"la presión total debe superar {WATER_VAPOR_MMHG} mmHg (vapor de agua): {p_total_mmhg}"
        )
    if not 0 < o2_fraction <= 1:
        raise ValueError(f"la fracción de O2 debe estar entre 0 y 1: {o2_fraction}")
    return (p_total_mmhg - WATER_VAPOR_MMHG) * o2_fraction


def co2_mmhg_to_percent(co2_mmhg: float, p_total_mmhg: float) -> float:
    """El mismo límite en mmHg es un porcentaje distinto a otra presión total."""
    return co2_mmhg / p_total_mmhg * 100


def co2_percent_to_mmhg(percent: float, p_total_mmhg: float) -> float:
    return percent / 100 * p_total_mmhg


def pressure_rate_psi_per_min(p_start_psi: float, p_end_psi: float, minutes: float) -> float:
    """Velocidad de cambio de presión (valor absoluto) en psi por minuto."""
    if minutes <= 0:
        raise ValueError("el tiempo debe ser positivo")
    return abs(p_end_psi - p_start_psi) / minutes
