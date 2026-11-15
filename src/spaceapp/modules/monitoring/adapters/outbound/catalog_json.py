"""Loads the rule catalog from a versioned JSON (the version is the content hash)."""

import hashlib
import json
from pathlib import Path
from typing import Any

from spaceapp.modules.monitoring.domain.rules import Rule, RuleCatalog


def _rule(raw: dict[str, Any]) -> Rule:
    data = {**raw}
    data["supersedes"] = tuple(data.get("supersedes", ()))
    data["params"] = dict(data.get("params", {}))
    return Rule(**data)


def load_catalog(path: Path | str) -> RuleCatalog:
    content = Path(path).read_bytes()
    raw = json.loads(content.decode("utf-8"))
    version = hashlib.sha256(content).hexdigest()[:12]
    return RuleCatalog(version=version, rules=tuple(_rule(r) for r in raw["rules"]))
