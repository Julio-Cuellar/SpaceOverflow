import pytest
from hypothesis import given
from hypothesis import strategies as st

from spaceapp.modules.monitoring.domain.physics import (
    co2_mmhg_to_percent,
    co2_percent_to_mmhg,
    partial_pressure_o2,
    pressure_rate_psi_per_min,
)
from spaceapp.modules.monitoring.domain.units import (
    kpa_to_mmhg,
    kpa_to_psi,
    mmhg_to_kpa,
    psi_to_kpa,
    psi_to_mmhg,
)


def test_standard_atmosphere_converts_between_units():
    assert kpa_to_mmhg(101.325) == pytest.approx(760.0, rel=1e-4)
    assert psi_to_mmhg(14.7) == pytest.approx(760.2, rel=1e-3)
    assert kpa_to_psi(psi_to_kpa(12.0)) == pytest.approx(12.0)
    assert mmhg_to_kpa(kpa_to_mmhg(56.5)) == pytest.approx(56.5)


@pytest.mark.parametrize(
    ("p_mmhg", "o2", "expected"),
    [
        (760.0, 0.21, 149.73),  # vector 1 from the context document
        (760.0, 0.18, 128.34),  # vector 2
        (kpa_to_mmhg(56.5), 0.34, 128.1),  # vector 3
    ],
)
def test_inspired_o2_partial_pressure_matches_the_context_vectors(p_mmhg, o2, expected):
    assert partial_pressure_o2(p_mmhg, o2) == pytest.approx(expected, abs=0.1)


def test_o2_is_evaluated_as_partial_pressure_not_as_percentage():
    # The same 21 % O2 stops being normoxia if the total pressure drops.
    assert partial_pressure_o2(kpa_to_mmhg(101.3), 0.21) > 145
    assert partial_pressure_o2(kpa_to_mmhg(70.0), 0.21) < 122


@pytest.mark.parametrize(("p", "f"), [(47.0, 0.21), (30.0, 0.21), (760.0, 0.0), (760.0, 1.2)])
def test_inspired_o2_rejects_impossible_inputs(p, f):
    with pytest.raises(ValueError, match=r"pressure|fraction"):
        partial_pressure_o2(p, f)


def test_the_same_co2_limit_is_a_different_percentage_at_other_pressures():
    # Context document: 3 mmHg = 0.39 % at 760 mmHg, but 0.71 % at 56.5 kPa.
    assert co2_mmhg_to_percent(3.0, 760.0) == pytest.approx(0.39, abs=0.01)
    assert co2_mmhg_to_percent(3.0, kpa_to_mmhg(56.5)) == pytest.approx(0.71, abs=0.01)


@given(st.floats(0.01, 10), st.floats(100, 900))
def test_co2_percentage_round_trips(mmhg, p):
    assert co2_percent_to_mmhg(co2_mmhg_to_percent(mmhg, p), p) == pytest.approx(mmhg)


@given(st.floats(100, 900), st.floats(0.05, 0.9), st.floats(0.0001, 0.05))
def test_pio2_grows_with_pressure_and_with_o2_fraction(p, f, delta):
    base = partial_pressure_o2(p, f)
    assert partial_pressure_o2(p + 1, f) > base
    assert partial_pressure_o2(p, min(1.0, f + delta)) >= base


def test_pressure_rate_is_the_absolute_change_per_minute():
    assert pressure_rate_psi_per_min(14.7, 12.0, 1.0) == pytest.approx(2.7)  # vector 5
    assert pressure_rate_psi_per_min(14.0, 0.0, 0.5) == pytest.approx(28.0)  # vector 6
    assert pressure_rate_psi_per_min(12.0, 14.7, 1.0) == pytest.approx(2.7)


def test_pressure_rate_needs_positive_time():
    with pytest.raises(ValueError, match="time"):
        pressure_rate_psi_per_min(14.7, 12.0, 0.0)
