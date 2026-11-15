"""What is read aloud: the answer body, without sources or symbols the voice garbles."""

from __future__ import annotations

from spaceapp.modules.assistant.application.speakable import MAX_CHARS, speakable


def test_the_sources_block_is_not_read() -> None:
    text = "The limit is 3 mmHg.\n\nSources: OCHMO-TB-004 CO₂ · V2 6004 · TB; NASA-STD-3001"

    assert "Sources" not in speakable(text)
    assert "OCHMO" not in speakable(text)


def test_the_source_label_after_each_template_passage_is_not_read() -> None:
    text = (
        "According to the loaded sources:\n"
        "- The cabin pressure is 5.0 psia. (NASA-STD-3001 Vol. 2 Rev F · VERIFIED)\n"
        "- It may not go lower. (OCHMO-TB-003 · V2 6002 · TB)"
    )

    spoken = speakable(text)

    assert "VERIFIED" not in spoken
    assert "V2 6002" not in spoken
    assert "The cabin pressure is" in spoken
    assert "It may not go lower." in spoken
    assert "\n" not in spoken


def test_symbols_and_units_are_spelled_out_so_the_voice_reads_them() -> None:
    spoken = speakable("Keep ppCO2 at or below 3 mmHg, between 34.5 kPa and 103 kPa; CO₂ ≤ 3.")

    assert "millimeters of mercury" in spoken
    assert "kilopascals" in spoken
    assert "carbon dioxide" in spoken
    assert "at most" in spoken
    assert "mmHg" not in spoken
    assert "≤" not in spoken


def test_markdown_and_requirement_brackets_are_dropped() -> None:
    spoken = speakable("**Note:** see [V2 6004] for the limit.")

    assert "*" not in spoken
    assert "[" not in spoken
    assert "V2 6004" in spoken


def test_a_long_text_is_cut_at_the_end_of_a_sentence_within_the_limit() -> None:
    sentence = "The crew must keep the average carbon dioxide level below the stated limit. "
    spoken = speakable(sentence * 20)

    assert len(spoken) <= MAX_CHARS
    assert spoken.endswith(".")


def test_a_single_very_long_sentence_is_cut_at_a_word() -> None:
    spoken = speakable("word " * 400)

    assert len(spoken) <= MAX_CHARS
    assert not spoken.endswith(" ")


def test_nothing_to_read_gives_an_empty_text() -> None:
    assert speakable("") == ""
    assert speakable("\n\nSources: X") == ""
