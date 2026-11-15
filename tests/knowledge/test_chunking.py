from __future__ import annotations

from itertools import pairwise

from spaceapp.modules.knowledge.ingest.chunking import chunk_page

DOC = "NASA-STD-3001 Vol. 2 Rev F"


def test_splits_a_page_at_each_requirement_reference() -> None:
    text = "[V2 6003] Normoxia 145 to 155 mmHg. [V2 6004] The ppCO2 average of 1 h shall be 3 mmHg."

    chunks = chunk_page(DOC, 12, text, "VERIFICADO")

    assert [c.requirement_ref for c in chunks] == ["V2 6003", "V2 6004"]
    assert chunks[1].content.startswith("[V2 6004]")
    assert all(c.page == 12 and c.document_code == DOC for c in chunks)
    assert all(c.evidence_state == "VERIFICADO" for c in chunks)


def test_text_before_the_first_reference_is_a_chunk_without_requirement() -> None:
    chunks = chunk_page(DOC, 1, "Intro before. [V1 4033] GCR limit 1.3 mSv per day.", "VERIFICADO")

    assert [c.requirement_ref for c in chunks] == [None, "V1 4033"]


def test_a_requirement_mentioned_inline_without_brackets_does_not_split_the_page() -> None:
    chunks = chunk_page(DOC, 1, "See V2 6004 for the limit. It is also in Table 6.2-1.", "TB")

    assert len(chunks) == 1
    assert chunks[0].requirement_ref is None


def test_long_text_is_split_with_overlap_and_every_part_is_short() -> None:
    text = " ".join(f"word{i}" for i in range(600))

    chunks = chunk_page("D", 1, text, "TB", max_chars=1000, overlap=100)

    assert len(chunks) > 1
    assert all(len(c.content) <= 1000 for c in chunks)
    # El comienzo de cada parte ya aparece al final de la anterior: no se pierde contexto.
    for before, after in pairwise(chunks):
        assert after.content[:30] in before.content


def test_every_part_of_a_long_requirement_keeps_its_reference() -> None:
    text = "[V2 6004] " + " ".join(f"limit{i}" for i in range(400))

    chunks = chunk_page(DOC, 3, text, "VERIFICADO", max_chars=800, overlap=80)

    assert len(chunks) > 1
    assert {c.requirement_ref for c in chunks} == {"V2 6004"}


def test_line_breaks_and_hyphenated_words_from_the_pdf_are_cleaned() -> None:
    chunks = chunk_page("D", 1, "carbon\ndioxide require-\nment holds", "TB")

    assert chunks[0].content == "carbon dioxide requirement holds"


def test_ids_are_deterministic_and_change_with_the_page() -> None:
    first = chunk_page("D", 1, "same text", "TB")
    again = chunk_page("D", 1, "same text", "TB")
    other_page = chunk_page("D", 2, "same text", "TB")

    assert first[0].id == again[0].id
    assert first[0].id != other_page[0].id


def test_blank_pages_produce_no_chunks() -> None:
    assert chunk_page("D", 1, "  \n \t ", "TB") == []
