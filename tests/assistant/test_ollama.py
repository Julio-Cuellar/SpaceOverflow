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
    excerpt="Dolor de cabeza entre 2.8 y 4.5 mmHg de ppCO₂.",
    evidence_state="TB",
)


def fake_opener(lines: Sequence[dict[str, object]], sent: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    """Imita urlopen: guarda el cuerpo enviado y devuelve las líneas NDJSON de respuesta."""

    def opener(request):  # type: ignore[no-untyped-def]
        sent.append(json.loads(request.data.decode("utf-8")))
        body = "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")
        return io.BytesIO(body)

    return opener


def test_yields_the_response_tokens_of_the_ndjson_stream() -> None:
    sent: list[dict[str, object]] = []
    gateway = OllamaGateway(
        model="modelo-pequeno",
        opener=fake_opener(
            [
                {"response": "Hola", "done": False},
                {"response": " mundo", "done": False},
                {"response": "", "done": True},
            ],
            sent,
        ),
    )

    tokens = list(gateway.stream("¿Qué pasa?", [PASSAGE], []))

    assert tokens == ["Hola", " mundo"]
    assert sent[0]["model"] == "modelo-pequeno"
    assert sent[0]["stream"] is True


def test_the_prompt_contains_only_the_retrieved_passages_and_the_no_information_rule() -> None:
    sent: list[dict[str, object]] = []
    gateway = OllamaGateway(model="m", opener=fake_opener([{"response": "", "done": True}], sent))

    list(gateway.stream("¿Qué pasa?", [PASSAGE], ["CO₂ alto (Alerta)"]))

    prompt = str(sent[0]["prompt"])
    assert "Dolor de cabeza entre 2.8 y 4.5 mmHg de ppCO₂." in prompt
    assert "No tengo esa información en las fuentes cargadas" in prompt
    assert "CO₂ alto (Alerta)" in prompt
