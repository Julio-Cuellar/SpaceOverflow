from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from spaceapp.modules.knowledge.adapters.outbound.ollama_embedder import OllamaEmbedder
from spaceapp.modules.knowledge.ports import EmbeddingError


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def opener(sent: list[dict[str, Any]], reply: Any = None, fail: Exception | None = None) -> Any:
    """Simulates `urlopen`: records what is sent and returns one vector per text (or `reply`)."""

    def open_url(request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        body = json.loads(request.data)  # type: ignore[arg-type]
        sent.append({"url": request.full_url, "body": body, "timeout": timeout})
        if fail is not None:
            raise fail
        default = {"embeddings": [[len(text), 1.0] for text in body["input"]]}
        return FakeResponse(json.dumps(reply if reply is not None else default).encode())

    return open_url


def test_sends_the_texts_to_the_embed_endpoint_and_returns_one_vector_each() -> None:
    sent: list[dict[str, Any]] = []
    embedder = OllamaEmbedder(model="bge-m3", opener=opener(sent))

    vectors = embedder.embed(["abc", "de"])

    assert vectors == [[3.0, 1.0], [2.0, 1.0]]
    assert sent[0]["url"].endswith("/api/embed")
    assert sent[0]["body"] == {"model": "bge-m3", "input": ["abc", "de"], "keep_alive": "30m"}


def test_asks_ollama_to_keep_the_model_loaded_so_a_question_does_not_pay_the_load_time() -> None:
    sent: list[dict[str, Any]] = []

    OllamaEmbedder(keep_alive="2h", opener=opener(sent)).embed(["a"])

    assert sent[0]["body"]["keep_alive"] == "2h"


def test_splits_long_lists_into_batches_and_keeps_the_order() -> None:
    sent: list[dict[str, Any]] = []
    embedder = OllamaEmbedder(batch_size=2, opener=opener(sent))

    vectors = embedder.embed(["a", "bb", "ccc", "dddd", "eeeee"])

    assert [len(call["body"]["input"]) for call in sent] == [2, 2, 1]
    assert [vector[0] for vector in vectors] == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_an_empty_list_does_not_call_the_server() -> None:
    sent: list[dict[str, Any]] = []

    assert OllamaEmbedder(opener=opener(sent)).embed([]) == []
    assert sent == []


def test_exposes_the_model_name_so_stored_vectors_can_be_matched_to_it() -> None:
    assert OllamaEmbedder(model="bge-m3").model == "bge-m3"


def test_the_request_has_a_time_limit() -> None:
    sent: list[dict[str, Any]] = []

    OllamaEmbedder(timeout_s=7.5, opener=opener(sent)).embed(["a"])

    assert sent[0]["timeout"] == 7.5


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("connection refused"),
        TimeoutError("too slow"),
        ConnectionResetError("reset"),
    ],
)
def test_a_network_failure_is_reported_as_an_embedding_error(failure: Exception) -> None:
    embedder = OllamaEmbedder(opener=opener([], fail=failure))

    with pytest.raises(EmbeddingError, match="Ollama"):
        embedder.embed(["a"])


@pytest.mark.parametrize(
    "reply",
    [
        {"error": 'model "bge-m3" not found'},
        {"embeddings": [[1.0]]},  # one vector for two texts
        {"embeddings": "no es una lista"},
        ["tampoco es un objeto"],
    ],
)
def test_a_reply_without_one_vector_per_text_is_an_embedding_error(reply: Any) -> None:
    embedder = OllamaEmbedder(opener=opener([], reply=reply))

    with pytest.raises(EmbeddingError):
        embedder.embed(["a", "b"])
