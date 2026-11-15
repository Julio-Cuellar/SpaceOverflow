"""Fragmenta el texto de una página en pasajes citables. Funciones puras, sin E/S.

Cada fragmento guarda documento, requisito, página, contenido y estado de evidencia, que es lo
que hace falta para citar (plan, F12.2). Se corta en cada referencia `[V2 6004]`; el texto largo
se parte en ventanas con solape corto para no perder contexto.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from spaceapp.modules.knowledge.domain.glossary import content_word_count

MAX_CHARS = 1200
OVERLAP = 150
# Por debajo de este número de palabras, un fragmento es un título o una entrada de índice.
MIN_CONTENT_WORDS = 6

_REQUIREMENT = re.compile(r"\[(V[12] \d{4})\]")
_HYPHEN_BREAK = re.compile(r"-\s*\n\s*")
_PARENTHESIS_WINDOW = 200


@dataclass(frozen=True)
class Chunk:
    id: str
    document_code: str
    requirement_ref: str | None
    page: int
    content: str
    evidence_state: str


def searchable_chunks(chunks: Iterable[Chunk]) -> list[Chunk]:
    """Los fragmentos citables: los títulos sueltos y las entradas de índice se descartan.

    La búsqueda por palabras y el cálculo de vectores usan la misma lista, para que cada
    fragmento tenga a la vez su puntaje léxico y su vector.
    """
    return [c for c in chunks if content_word_count(c.content) >= MIN_CONTENT_WORDS]


def clean(text: str) -> str:
    """Une las palabras partidas por guion al final de línea y colapsa los espacios."""
    return " ".join(_HYPHEN_BREAK.sub("", text).split())


def _starts_a_requirement(text: str, match: re.Match[str]) -> bool:
    """Una referencia abre un requisito; si está citada dentro de una frase, no.

    La norma cita otros requisitos a mitad de oración («…ver [V2 6004] Nominal…», «(… [V1 4033])»).
    Partir ahí corta frases y atribuye texto al requisito equivocado. Una cita queda precedida por
    una palabra en minúscula, un paréntesis o una coma; un requisito, por un punto, un corchete
    de cierre, un número de página o el inicio del texto. Si hay un paréntesis sin cerrar antes
    de la referencia («(… NASA-STD-3001, Volume 1 [V1 4030] Título)»), también es una cita aunque
    la preceda un dígito.
    """
    before = text[: match.start()].rstrip()
    if before == "":
        return True
    if before[-1].islower() or before[-1] in "(,":
        return False
    return not _inside_open_parenthesis(before)


def _inside_open_parenthesis(before: str) -> bool:
    # Solo se mira el tramo reciente: un paréntesis olvidado muy atrás no puede decidir.
    recent = before[-_PARENTHESIS_WINDOW:]
    return recent.count("(") > recent.count(")")


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Se corta en un espacio dentro de la segunda mitad de la ventana, no a media palabra.
            space = text.rfind(" ", start + max_chars // 2, end)
            if space > start:
                end = space
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
        next_space = text.find(" ", start, end)
        if next_space != -1:
            start = next_space + 1
    return parts


def _chunk_id(document_code: str, page: int, index: int, content: str) -> str:
    raw = f"{document_code}|{page}|{index}|{content}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def chunk_page(
    document_code: str,
    page: int,
    text: str,
    evidence_state: str,
    max_chars: int = MAX_CHARS,
    overlap: int = OVERLAP,
) -> list[Chunk]:
    cleaned = clean(text)
    if not cleaned:
        return []

    segments: list[tuple[str | None, str]] = []
    matches = [m for m in _REQUIREMENT.finditer(cleaned) if _starts_a_requirement(cleaned, m)]
    if not matches:
        segments.append((None, cleaned))
    else:
        if matches[0].start() > 0:
            segments.append((None, cleaned[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
            segments.append((match.group(1), cleaned[match.start() : end].strip()))

    chunks: list[Chunk] = []
    for requirement_ref, segment in segments:
        for part in _split_long(segment, max_chars, overlap):
            chunks.append(
                Chunk(
                    id=_chunk_id(document_code, page, len(chunks), part),
                    document_code=document_code,
                    requirement_ref=requirement_ref,
                    page=page,
                    content=part,
                    evidence_state=evidence_state,
                )
            )
    return chunks
