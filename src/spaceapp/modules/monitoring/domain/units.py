"""Conversiones de presión. Las reglas de atmósfera trabajan en mmHg (presión parcial)."""

KPA_TO_MMHG = 7.50062
PSI_TO_MMHG = 51.7149


def kpa_to_mmhg(kpa: float) -> float:
    return kpa * KPA_TO_MMHG


def mmhg_to_kpa(mmhg: float) -> float:
    return mmhg / KPA_TO_MMHG


def psi_to_mmhg(psi: float) -> float:
    return psi * PSI_TO_MMHG


def psi_to_kpa(psi: float) -> float:
    return psi * PSI_TO_MMHG / KPA_TO_MMHG


def kpa_to_psi(kpa: float) -> float:
    return kpa * KPA_TO_MMHG / PSI_TO_MMHG
