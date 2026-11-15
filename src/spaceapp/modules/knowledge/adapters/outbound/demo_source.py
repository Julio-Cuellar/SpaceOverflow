"""Adaptador de demostración: lee el catálogo JSON versionado. Toda salida se etiqueta DEMO."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spaceapp.modules.knowledge.domain.model import (
    Action,
    Citation,
    EvidenceState,
    Guidance,
    UnknownRuleError,
)
from spaceapp.modules.knowledge.domain.search import Indexed, normalize, rank

DEMO_NOTICE = "Esta recomendación usa un dato de demostración, no de NASA."


class DemoKnowledgeSource:
    def __init__(self, catalog: dict[str, Any]) -> None:
        self._rules: dict[str, dict[str, Any]] = {rule["key"]: rule for rule in catalog["rules"]}
        self._passages: list[Indexed[Citation]] = [
            Indexed(
                item=Citation(
                    document_code=p["document_code"],
                    requirement_ref=p.get("requirement_ref"),
                    page=p.get("page"),
                    excerpt=p["excerpt"],
                    evidence_state=EvidenceState(p["evidence_state"]),
                ),
                keywords=frozenset(normalize(word) for word in p["keywords"]),
            )
            for p in catalog.get("passages", [])
        ]
        self._actions: dict[str, Action] = {
            key: Action(key=key, title=value["title"], description=value["description"])
            for key, value in catalog["actions"].items()
        }

    @classmethod
    def from_file(cls, path: Path) -> DemoKnowledgeSource:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def rule_keys(self) -> list[str]:
        return list(self._rules)

    def guidance_for(self, rule_key: str) -> Guidance:
        rule = self._rules.get(rule_key)
        if rule is None:
            raise UnknownRuleError(rule_key)
        return Guidance(
            rule_key=rule_key,
            source_kind="DEMO",
            body=f"{DEMO_NOTICE} {rule['text']}",
            actions=tuple(self._actions[key] for key in rule["action_keys"]),
            citations=tuple(
                Citation(
                    document_code=c["document_code"],
                    requirement_ref=c.get("requirement_ref"),
                    page=c.get("page"),
                    excerpt=c["excerpt"],
                    evidence_state=EvidenceState(c["evidence_state"]),
                )
                for c in rule["citations"]
            ),
        )

    def action(self, key: str) -> Action | None:
        return self._actions.get(key)

    def action_title(self, key: str) -> str | None:
        action = self._actions.get(key)
        return action.title if action else None

    def search(self, text: str, k: int) -> list[Citation]:
        """Pasajes citables que responden a la pregunta. Vacío si ninguno es relevante."""
        return rank(text, self._passages, k)
