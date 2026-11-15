from datetime import UTC, datetime, timedelta

from spaceapp.modules.monitoring.domain.series import Sample, latest, mean, within

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def s(offset: int, value: float) -> Sample:
    return Sample(T0 + timedelta(seconds=offset), value)


def test_within_includes_both_ends_and_ignores_the_rest():
    samples = [s(0, 1), s(10, 2), s(20, 3), s(30, 4)]
    got = within(samples, T0 + timedelta(seconds=10), T0 + timedelta(seconds=20))
    assert [x.value for x in got] == [2, 3]


def test_mean_of_nothing_is_none_not_zero():
    assert mean([]) is None
    assert mean([s(0, 2), s(1, 4)]) == 3


def test_latest_returns_the_most_recent_sample_even_if_unordered():
    assert latest([s(5, 1), s(30, 9), s(10, 2)]) == s(30, 9)
    assert latest([]) is None
