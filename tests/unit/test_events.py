from typing import ClassVar
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spaceapp.platform.events import EventEnvelope, EventPayload


class Pinged(EventPayload):
    event_type: ClassVar[str] = "demo.pinged"
    n: int


def make(n: int = 1) -> EventEnvelope:
    return EventEnvelope.from_payload(
        Pinged(n=n), aggregate_type="demo", aggregate_id=uuid4(), partition_key="habitat:h1"
    )


def test_envelope_takes_its_type_from_the_payload_class():
    assert make().type == "demo.pinged"


def test_envelope_has_unique_ids_and_defaults():
    a, b = make(), make()
    assert a.event_id != b.event_id
    assert a.version == 1
    assert a.occurred_at.tzinfo is not None


def test_envelope_keeps_correlation_and_causation():
    corr, cause = uuid4(), uuid4()
    e = EventEnvelope.from_payload(
        Pinged(n=1),
        aggregate_type="demo",
        aggregate_id=uuid4(),
        partition_key="k",
        correlation_id=corr,
        causation_id=cause,
    )
    assert (e.correlation_id, e.causation_id) == (corr, cause)


@pytest.mark.parametrize("bad", ["Monitoring.AlertRaised", "alert_raised", "a.b.c", "", "x."])
def test_event_type_must_be_module_dot_fact_in_snake_case(bad: str):
    with pytest.raises(ValidationError):
        EventEnvelope(
            type=bad, aggregate_type="demo", aggregate_id=uuid4(), partition_key="k", payload={}
        )


def test_payload_can_be_read_back_as_its_model():
    assert make(7).payload_as(Pinged) == Pinged(n=7)


def test_payload_as_rejects_the_wrong_model():
    class Other(EventPayload):
        event_type: ClassVar[str] = "demo.other"
        n: int

    with pytest.raises(ValueError, match=r"demo\.pinged"):
        make().payload_as(Other)


def test_json_round_trip_is_lossless():
    e = make(3)
    assert EventEnvelope.model_validate_json(e.model_dump_json()) == e
