from __future__ import annotations

import json
from pathlib import Path

import pytest
from pdf_helpers import make_pdf

from spaceapp.modules.knowledge.ingest.__main__ import main
from spaceapp.modules.knowledge.ingest.chunking import chunk_page
from spaceapp.modules.knowledge.ingest.manifest import DocumentEntry
from spaceapp.modules.knowledge.ingest.pipeline import ingest_manifest, ingest_pdf
from spaceapp.modules.knowledge.ingest.store import InMemoryChunkStore, JsonlChunkStore

TEXT = "[V2 6004] The ppCO2 average of 1 h shall be 3 mmHg or less."


def entry(code: str, filename: str, *, read: bool = True, optional: bool = False) -> DocumentEntry:
    return DocumentEntry(
        code=code,
        title=code,
        url=f"https://example.org/{filename}",
        kind="norma",
        evidence_state="VERIFICADO",
        license_status="no_verificada",
        packageable=False,
        read=read,
        optional=optional,
    )


def write_pdf(directory: Path, filename: str, pages: list[str]) -> None:
    (directory / filename).write_bytes(make_pdf(pages))


class TestStore:
    def test_ignores_a_chunk_that_is_already_stored(self) -> None:
        store = InMemoryChunkStore()
        chunks = chunk_page("D", 1, "some text", "TB")

        assert store.add(chunks) == 1
        assert store.add(chunks) == 0
        assert len(store.all()) == 1

    def test_the_file_store_keeps_the_chunks_between_runs(self, tmp_path: Path) -> None:
        path = tmp_path / "index" / "chunks.jsonl"
        JsonlChunkStore(path).add(chunk_page("D", 1, TEXT, "VERIFICADO"))

        reloaded = JsonlChunkStore(path)

        assert [c.requirement_ref for c in reloaded.all()] == ["V2 6004"]
        assert reloaded.add(chunk_page("D", 1, TEXT, "VERIFICADO")) == 0


class TestIngestPdf:
    def test_stores_each_page_as_citable_chunks(self, tmp_path: Path) -> None:
        write_pdf(tmp_path, "doc.pdf", ["intro text here", TEXT])
        store = InMemoryChunkStore()

        result = ingest_pdf(entry("DOC", "doc.pdf"), tmp_path / "doc.pdf", store)

        stored = store.all()
        assert result.added == len(stored) > 0
        refs = {(c.page, c.requirement_ref) for c in stored}
        assert (2, "V2 6004") in refs
        assert all(c.document_code == "DOC" and c.evidence_state == "VERIFICADO" for c in stored)

    def test_running_it_twice_does_not_duplicate_anything(self, tmp_path: Path) -> None:
        write_pdf(tmp_path, "doc.pdf", [TEXT])
        store = InMemoryChunkStore()

        first = ingest_pdf(entry("DOC", "doc.pdf"), tmp_path / "doc.pdf", store)
        second = ingest_pdf(entry("DOC", "doc.pdf"), tmp_path / "doc.pdf", store)

        assert first.added > 0
        assert second.added == 0
        assert second.chunks == first.chunks


class TestIngestManifest:
    def test_reports_what_was_ingested_what_is_missing_and_what_was_skipped(
        self, tmp_path: Path
    ) -> None:
        write_pdf(tmp_path, "good.pdf", [TEXT])
        entries = [
            entry("GOOD", "good.pdf"),
            entry("MISSING", "missing.pdf"),
            entry("UNOPENED", "unopened.pdf", read=False, optional=True),
        ]

        report = ingest_manifest(entries, tmp_path, InMemoryChunkStore())

        assert report.ingested == ["GOOD"]
        assert report.missing == ["MISSING"]
        assert report.skipped == ["UNOPENED"]

    def test_optional_documents_are_only_attempted_when_asked(self, tmp_path: Path) -> None:
        entries = [entry("UNOPENED", "unopened.pdf", read=False, optional=True)]

        report = ingest_manifest(entries, tmp_path, InMemoryChunkStore(), include_optional=True)

        assert report.missing == ["UNOPENED"]
        assert report.skipped == []

    def test_a_pdf_without_extractable_text_is_flagged_instead_of_ignored(
        self, tmp_path: Path
    ) -> None:
        write_pdf(tmp_path, "scan.pdf", ["", ""])

        report = ingest_manifest([entry("SCAN", "scan.pdf")], tmp_path, InMemoryChunkStore())

        assert report.empty == ["SCAN"]
        assert report.ingested == []

    def test_a_broken_pdf_does_not_stop_the_other_documents(self, tmp_path: Path) -> None:
        (tmp_path / "broken.pdf").write_bytes(b"not a pdf")
        write_pdf(tmp_path, "good.pdf", [TEXT])

        report = ingest_manifest(
            [entry("BROKEN", "broken.pdf"), entry("GOOD", "good.pdf")],
            tmp_path,
            InMemoryChunkStore(),
        )

        assert report.failed == ["BROKEN"]
        assert report.ingested == ["GOOD"]


class TestCommand:
    def write_manifest(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "documents": [
                        {
                            "code": "GOOD",
                            "title": "GOOD",
                            "url": "https://example.org/good.pdf",
                            "kind": "norma",
                            "evidence_state": "VERIFICADO",
                            "license_status": "no_verificada",
                            "packageable": False,
                            "read": True,
                            "optional": False,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_indexes_the_pdfs_and_prints_a_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self.write_manifest(tmp_path / "manifest.json")
        write_pdf(tmp_path, "good.pdf", [TEXT])
        out = tmp_path / "index" / "chunks.jsonl"

        code = main(
            [
                "--manifest",
                str(tmp_path / "manifest.json"),
                "--pdf-dir",
                str(tmp_path),
                "--out",
                str(out),
            ]
        )

        assert code == 0
        assert out.exists()
        assert "GOOD" in capsys.readouterr().out

    def test_rejects_an_invalid_manifest_with_a_clear_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "manifest.json").write_text(
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

        code = main(["--manifest", str(tmp_path / "manifest.json"), "--pdf-dir", str(tmp_path)])

        assert code == 2
        assert "licencia" in capsys.readouterr().err

    def test_exits_with_an_error_code_when_nothing_could_be_indexed(self, tmp_path: Path) -> None:
        self.write_manifest(tmp_path / "manifest.json")

        code = main(
            [
                "--manifest",
                str(tmp_path / "manifest.json"),
                "--pdf-dir",
                str(tmp_path),
                "--out",
                str(tmp_path / "chunks.jsonl"),
            ]
        )

        assert code == 1
