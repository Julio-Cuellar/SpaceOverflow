"""Ingestion: from PDF to citable chunks. Idempotent: running it again duplicates nothing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from spaceapp.modules.knowledge.ingest.chunking import chunk_page
from spaceapp.modules.knowledge.ingest.manifest import DocumentEntry
from spaceapp.modules.knowledge.ingest.pdf import PdfReadError, extract_pages
from spaceapp.modules.knowledge.ingest.store import ChunkStore


@dataclass(frozen=True)
class PdfIngest:
    chunks: int
    added: int


@dataclass
class IngestReport:
    ingested: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    chunks_added: int = 0


def ingest_pdf(entry: DocumentEntry, pdf_path: Path, store: ChunkStore) -> PdfIngest:
    pages = extract_pages(pdf_path)
    chunks = [
        chunk
        for number, text in enumerate(pages, start=1)
        for chunk in chunk_page(entry.code, number, text, entry.evidence_state)
    ]
    return PdfIngest(chunks=len(chunks), added=store.add(chunks))


def ingest_manifest(
    entries: list[DocumentEntry],
    pdf_dir: Path,
    store: ChunkStore,
    include_optional: bool = False,
) -> IngestReport:
    """Indexes the documents that were read. A document with problems does not stop the others."""
    report = IngestReport()
    for entry in entries:
        if not (entry.indexed_by_default or (include_optional and entry.optional)):
            report.skipped.append(entry.code)
            continue

        pdf_path = pdf_dir / entry.filename
        if not pdf_path.exists():
            report.missing.append(entry.code)
            continue

        try:
            result = ingest_pdf(entry, pdf_path, store)
        except PdfReadError:
            report.failed.append(entry.code)
            continue

        if result.chunks == 0:
            # No extractable text: usually a scan. It is flagged instead of ignored.
            report.empty.append(entry.code)
        else:
            report.ingested.append(entry.code)
            report.chunks_added += result.added
    return report
