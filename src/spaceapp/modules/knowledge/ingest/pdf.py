"""Lectura de PDFs: texto por página, con errores claros. Funciona sin internet."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class PdfReadError(Exception):
    """No se pudo leer el archivo: no existe o no es un PDF válido."""


def extract_pages(path: Path) -> list[str]:
    """Texto de cada página, en orden. Las tablas que vienen como imagen no salen aquí."""
    try:
        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    except FileNotFoundError as error:
        raise PdfReadError(f"no existe el archivo: {path}") from error
    except (PyPdfError, OSError) as error:
        raise PdfReadError(f"no se pudo leer {path.name}: {error}") from error
