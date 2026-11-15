from __future__ import annotations

import io
import json
from collections.abc import Sequence

from spaceapp.modules.assistant.adapters.outbound.ollama import OllamaGateway
from spaceapp.modules.knowledge.contracts import CitationDTO

PASSAGE = CitationDTO(
    document_code="OCHMO-TB-004 CO₂",
    requirement_ref=None,
    page=None,
    excerpt="Headache between 2.8 and 4.5 mmHg of ppCO₂.",
    evidence_state="TB",
)


def fake_opener(lines: Sequence[dict[str, object]], sent: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    """Imitates urlopen: stores the sent body and returns the NDJSON response lines."""

    def opener(request):  # type: ignore[no-untyped-def]
        sent.append(json.loads(request.data.decode("utf-8")))
        body = "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")
        return io.BytesIO(body)

    return opener


def test_yields_the_response_tokens_of_the_ndjson_stream() -> None:
    sent: list[dict[str, object]] = []
    gateway = OllamaGateway(
        model="small-model",
        opener=fake_opener(
            [
                {"response": "Hello", "done": False},
                {"response": " world", "done": False},
                {"response": "", "done": True},
            ],
            sent,
        ),
    )

    tokens = list(gateway.stream("What is happening?", [PASSAGE], []))

    assert tokens == ["Hello", " world"]
    assert sent[0]["model"] == "small-model"
    assert sent[0]["stream"] is True


def test_the_prompt_contains_only_the_retrieved_passages_and_the_no_information_rule() -> None:
    sent: list[dict[str, object]] = []
    gateway = OllamaGateway(model="m", opener=fake_opener([{"response": "", "done": True}], sent))

    list(gateway.stream("What is happening?", [PASSAGE], ["High CO₂ (Alert)"]))

    prompt = str(sent[0]["prompt"])
    assert "Headache between 2.8 and 4.5 mmHg of ppCO₂." in prompt
    assert "I don't have that information in the loaded sources" in prompt
    assert "High CO₂ (Alert)" in prompt
