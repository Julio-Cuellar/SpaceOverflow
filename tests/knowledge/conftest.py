from __future__ import annotations

from pathlib import Path

import pytest

from spaceapp.modules.knowledge.adapters.outbound.demo_source import DemoKnowledgeSource

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_CATALOG = PROJECT_ROOT / "data" / "knowledge" / "demo_catalog.json"


@pytest.fixture
def demo_source() -> DemoKnowledgeSource:
    return DemoKnowledgeSource.from_file(DEMO_CATALOG)
