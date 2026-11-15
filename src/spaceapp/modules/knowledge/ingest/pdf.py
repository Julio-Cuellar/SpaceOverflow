"""PDF reading: text per page, with clear errors. It works without internet."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class PdfReadError(Exception):
    """The file could not be read: it does not exist or is not a valid PDF."""


def extract_pages(path: Path) -> list[str]:
    """Text of each page, in order. Tables that come as an image do not appear here."""
    try:
        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    except FileNotFoundError as error:
        raise PdfReadError(f"the file does not exist: {path}") from error
    except (PyPdfError, OSError) as error:
        raise PdfReadError(f"no se pudo leer {path.name}: {error}") from error
