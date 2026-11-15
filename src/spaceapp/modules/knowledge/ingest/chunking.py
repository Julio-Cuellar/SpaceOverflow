"""Splits the text of a page into citable passages. Pure functions, no I/O.

Each fragment keeps document, requirement, page, content and evidence state, which is what is
needed to cite (plan, F12.2). It is cut at every `[V2 6004]` reference; long text is split into
windows with a short overlap so no context is lost.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from spaceapp.modules.knowledge.domain.terms import content_word_count

MAX_CHARS = 1200
OVERLAP = 150
# Below this number of words, a fragment is a title or an index entry.
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
    """The citable fragments: loose titles and index entries are discarded.

    Word search and the vector computation use the same list, so that every fragment has both its
    lexical score and its vector.
    """
    return [c for c in chunks if content_word_count(c.content) >= MIN_CONTENT_WORDS]


def clean(text: str) -> str:
    """Joins words split by a hyphen at the end of a line and collapses the spaces."""
    return " ".join(_HYPHEN_BREAK.sub("", text).split())


def _starts_a_requirement(text: str, match: re.Match[str]) -> bool:
    """A reference opens a requirement; if it is cited inside a sentence, it does not.

    The standard cites other requirements mid-sentence ('...see [V2 6004] Nominal...',
    '(... [V1 4033])'). Splitting there cuts sentences and attributes text to the wrong requirement.
    A citation is preceded by a lowercase word, a parenthesis or a comma; a requirement, by a
    period, a closing bracket, a page number or the start of the text. If there is an unclosed
    parenthesis before the reference ('(... NASA-STD-3001, Volume 1 [V1 4030] Title)'), it is also
    a citation even if a digit precedes it.
    """
    before = text[: match.start()].rstrip()
    if before == "":
        return True
    if before[-1].islower() or before[-1] in "(,":
        return False
    return not _inside_open_parenthesis(before)


def _inside_open_parenthesis(before: str) -> bool:
    # Only the recent stretch is looked at: a forgotten parenthesis far back cannot decide.
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
            # It is cut at a space within the second half of the window, not mid-word.
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
