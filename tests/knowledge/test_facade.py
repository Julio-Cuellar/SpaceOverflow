from __future__ import annotations

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource
from spaceapp.modules.knowledge.contracts import CitationDTO
from spaceapp.modules.knowledge.facade import ActionCatalogQuery, KnowledgeQuery


def test_action_catalog_returns_title_and_description_of_an_action(
    demo_source: DemoKnowledgeSource,
) -> None:
    query = ActionCatalogQuery(demo_source)

    info = query.get("revisar_ventilacion_y_filtros")

    assert info is not None
    assert info.title
    assert info.description


def test_knowledge_query_returns_citable_passages_as_contract_dtos(
    demo_source: DemoKnowledgeSource,
) -> None:
    passages = KnowledgeQuery(demo_source).search("dolor de cabeza", k=2)

    assert passages
    assert all(isinstance(p, CitationDTO) for p in passages)
    assert passages[0].document_code == "OCHMO-TB-004 CO₂"
    assert passages[0].evidence_state == "TB"


def test_action_catalog_returns_none_for_an_unknown_action(
    demo_source: DemoKnowledgeSource,
) -> None:
    assert ActionCatalogQuery(demo_source).get("accion_inventada") is None
