"""Document manifest: what is indexed, where it comes from and what license it has.

Plan rule (F12.1): **no PDF is packaged without a confirmed license**. The doubtful ones are
indexed locally only and documented.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

EVIDENCE_STATES = frozenset({"VERIFIED", "TB", "DEMO", "UNVERIFIED"})
LICENSE_CONFIRMED = "confirmed"
_REQUIRED = (
    "code",
    "title",
    "url",
    "kind",
    "evidence_state",
    "license_status",
    "packageable",
    "read",
    "optional",
)


class ManifestError(ValueError):
    """The manifest does not meet the license rules or is missing fields."""


@dataclass(frozen=True)
class DocumentEntry:
    code: str
    title: str
    url: str
    kind: str
    evidence_state: str
    license_status: str
    packageable: bool
    read: bool
    optional: bool
    note: str = ""

    @property
    def filename(self) -> str:
        return PurePosixPath(urlparse(self.url).path).name

    @property
    def indexed_by_default(self) -> bool:
        """Only what someone opened and read, and that is not optional."""
        return self.read and not self.optional


def _entry(raw: dict[str, Any]) -> DocumentEntry:
    missing = [key for key in _REQUIRED if key not in raw]
    if missing:
        raise ManifestError(f"{raw.get('code', '?')}: faltan campos {missing}")
    if raw["evidence_state"] not in EVIDENCE_STATES:
        raise ManifestError(f"{raw['code']}: estado de evidencia desconocido")
    if raw["packageable"] and raw["license_status"] != LICENSE_CONFIRMED:
        raise ManifestError(f"{raw['code']}: cannot be packaged without a confirmed license")
    return DocumentEntry(
        code=raw["code"],
        title=raw["title"],
        url=raw["url"],
        kind=raw["kind"],
        evidence_state=raw["evidence_state"],
        license_status=raw["license_status"],
        packageable=bool(raw["packageable"]),
        read=bool(raw["read"]),
        optional=bool(raw["optional"]),
        note=raw.get("note", ""),
    )


def load_manifest(path: Path) -> list[DocumentEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = [_entry(item) for item in raw["documents"]]
    codes = [entry.code for entry in entries]
    if len(codes) != len(set(codes)):
        raise ManifestError("there are repeated document codes")
    return entries
