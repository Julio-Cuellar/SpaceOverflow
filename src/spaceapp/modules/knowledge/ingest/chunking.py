"""Fragmenta el texto de una página en pasajes citables. Funciones puras, sin E/S.

Cada fragmento guarda documento, requisito, página, contenido y estado de evidencia, que es lo
que hace falta para citar (plan, F12.2). Se corta en cada referencia `[V2 6004]`; el texto largo
se parte en ventanas con solape corto para no perder contexto.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_CHARS = 1200
OVERLAP = 150

_REQUIREMENT = re.compile(r"\[(V[12] \d{4})\]")
_HYPHEN_BREAK = re.compile(r"-\s*\n\s*")


@dataclass(frozen=True)
class Chunk:
    id: str
    document_code: str
    requirement_ref: str | None
    page: int
    content: str
    evidence_state: str


def clean(text: str) -> str:
    """Une las palabras partidas por guion al final de línea y colapsa los espacios."""
    return " ".join(_HYPHEN_BREAK.sub("", text).split())


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
    matches = list(_REQUIREMENT.finditer(cleaned))
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
