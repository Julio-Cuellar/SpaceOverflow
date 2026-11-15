from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from spaceapp.modules.knowledge.contracts import AlertRaised, RecommendationReady


def test_recommendation_ready_has_exactly_the_payload_of_the_plan() -> None:
    event = RecommendationReady(
        alert_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        action_keys=["revisar_ventilacion_y_filtros"],
        citations=[
            {
                "document_code": "NASA-STD-3001 Vol. 2 Rev F",
                "requirement_ref": "V2 6004",
                "page": None,
                "excerpt": "ppCO2 promedio de 1 h ≤ 3 mmHg",
                "evidence_state": "VERIFICADO",
            }
        ],
    )

    assert set(event.model_dump().keys()) == {
        "alert_id",
        "recommendation_id",
        "action_keys",
        "citations",
    }


def test_alert_raised_requires_the_rule_key() -> None:
    with pytest.raises(ValidationError):
        AlertRaised.model_validate(
            {
                "event_id": str(uuid.uuid4()),
                "alert_id": str(uuid.uuid4()),
                "zone_id": None,
                "severity": "ALERTA",
                "evidence": {},
                "cause_hint": "AMBIENTE",
            }
        )


def test_citation_rejects_an_evidence_state_outside_the_contract() -> None:
    with pytest.raises(ValidationError):
        RecommendationReady.model_validate(
            {
                "alert_id": str(uuid.uuid4()),
                "recommendation_id": str(uuid.uuid4()),
                "action_keys": ["x"],
                "citations": [
                    {
                        "document_code": "d",
                        "requirement_ref": None,
                        "page": None,
                        "excerpt": "e",
                        "evidence_state": "SIMULADO",
                    }
                ],
            }
        )
