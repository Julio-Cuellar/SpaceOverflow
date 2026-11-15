from __future__ import annotations

from pathlib import Path

import pytest
from pdf_helpers import make_pdf

from spaceapp.modules.knowledge.ingest.pdf import PdfReadError, extract_pages


def test_extracts_the_text_of_each_page_in_order(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf(["first page text", "second page text"]))

    pages = extract_pages(pdf)

    assert [p.strip() for p in pages] == ["first page text", "second page text"]


def test_a_missing_file_raises_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(PdfReadError):
        extract_pages(tmp_path / "missing.pdf")


def test_a_file_that_is_not_a_pdf_raises_a_clear_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a pdf")

    with pytest.raises(PdfReadError):
        extract_pages(broken)
