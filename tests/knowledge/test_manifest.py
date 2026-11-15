from __future__ import annotations

import json
from pathlib import Path

import pytest

from spaceapp.modules.knowledge.ingest.manifest import ManifestError, load_manifest

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "manifest.json"


def test_lists_the_seven_documents_read_for_the_plan() -> None:
    read = {d.code for d in load_manifest(MANIFEST) if d.read}

    assert read == {
        "NASA-STD-3001 Vol. 1 Rev C",
        "NASA-STD-3001 Vol. 2 Rev F",
        "OCHMO-TB-002 ECLSS",
        "OCHMO-TB-003 atmósfera habitable",
        "OCHMO-TB-004 CO₂",
        "OCHMO-TB-044 operaciones médicas",
        "Checklist del botiquín médico",
    }


def test_standards_are_verified_and_technical_briefs_are_tb() -> None:
    by_code = {d.code: d for d in load_manifest(MANIFEST)}

    assert by_code["NASA-STD-3001 Vol. 2 Rev F"].evidence_state == "VERIFICADO"
    assert by_code["OCHMO-TB-004 CO₂"].evidence_state == "TB"


def test_no_document_is_packageable_until_its_license_is_confirmed() -> None:
    for document in load_manifest(MANIFEST):
        assert not document.packageable or document.license_status == "confirmada", document.code


def test_unopened_documents_are_optional_and_not_indexed_by_default() -> None:
    documents = load_manifest(MANIFEST)
    unopened = [d for d in documents if not d.read]

    assert unopened
    assert all(d.optional for d in unopened)
    assert not any(d.indexed_by_default for d in unopened)


def test_the_pdf_filename_comes_from_the_url() -> None:
    by_code = {d.code: d for d in load_manifest(MANIFEST)}

    assert by_code["OCHMO-TB-004 CO₂"].filename == "co2-technical-brief-ochmo.pdf"


def test_rejects_a_manifest_that_packages_a_document_with_an_unconfirmed_license(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "manifest.json"
    bad.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "code": "X",
                        "title": "X",
                        "url": "https://example.org/x.pdf",
                        "kind": "norma",
                        "evidence_state": "VERIFICADO",
                        "license_status": "no_verificada",
                        "packageable": True,
                        "read": True,
                        "optional": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        load_manifest(bad)
