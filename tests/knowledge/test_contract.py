from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from spaceapp.modules.assistant.contracts import AnswerReady
from spaceapp.modules.knowledge.contracts import RecommendationEnriched, RecommendationReady
from spaceapp.platform.events import EventPayload
from spaceapp.platform.vocab import Citation

CITATION = {
    "document_code": "NASA-STD-3001 Vol. 2 Rev F",
    "requirement_ref": "V2 6004",
    "page": None,
    "excerpt": "1 h average ppCO2 ≤ 3 mmHg",
    "evidence_state": "VERIFIED",
}


def test_the_events_of_my_modules_are_event_payloads_with_a_module_dot_fact_type() -> None:
    for model, event_type in (
        (RecommendationReady, "knowledge.recommendation_ready"),
        (RecommendationEnriched, "knowledge.recommendation_enriched"),
        (AnswerReady, "assistant.answer_ready"),
    ):
        assert issubclass(model, EventPayload)
        assert model.event_type == event_type


def test_recommendation_ready_has_exactly_the_payload_of_the_plan() -> None:
    event = RecommendationReady(
        alert_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        action_keys=["check_ventilation_and_filters"],
        citations=[Citation.model_validate(CITATION)],
    )

    assert set(event.model_dump().keys()) == {
        "alert_id",
        "recommendation_id",
        "action_keys",
        "citations",
    }


def test_citations_are_the_shared_kernel_type_not_a_private_copy() -> None:
    from spaceapp.modules.knowledge.contracts import CitationDTO

    assert CitationDTO is Citation


def test_a_payload_with_an_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RecommendationReady.model_validate(
            {
                "alert_id": str(uuid.uuid4()),
                "recommendation_id": str(uuid.uuid4()),
                "action_keys": ["x"],
                "citations": [CITATION],
                "extra": 1,
            }
        )


def test_citation_rejects_an_evidence_state_outside_the_contract() -> None:
    with pytest.raises(ValidationError):
        RecommendationReady.model_validate(
            {
                "alert_id": str(uuid.uuid4()),
                "recommendation_id": str(uuid.uuid4()),
                "action_keys": ["x"],
                "citations": [{**CITATION, "evidence_state": "SIMULATED"}],
            }
        )
