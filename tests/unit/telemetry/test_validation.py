from datetime import UTC, datetime
from uuid import uuid4

import pytest

from spaceapp.modules.telemetry.domain.readings import (
    MAX_BATCH,
    InvalidBatch,
    ReadingIn,
    validate_batch,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
S = uuid4()


def r(**over) -> ReadingIn:
    return ReadingIn(**{"sensor_id": S, "ts": NOW, "value": 1.0, "quality": "ok", **over})


def test_a_valid_batch_passes():
    validate_batch([r(), r(value=2.0)])


def test_an_empty_batch_is_rejected():
    with pytest.raises(InvalidBatch, match="vacío"):
        validate_batch([])


def test_a_batch_cannot_exceed_500_readings():
    assert MAX_BATCH == 500
    validate_batch([r() for _ in range(500)])
    with pytest.raises(InvalidBatch, match="500"):
        validate_batch([r() for _ in range(501)])


def test_timestamps_must_carry_a_timezone():
    with pytest.raises(InvalidBatch, match="zona horaria"):
        validate_batch([r(ts=datetime(2026, 11, 14, 12, 0))])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_values_must_be_finite_numbers(bad):
    with pytest.raises(InvalidBatch, match="finito"):
        validate_batch([r(value=bad)])
