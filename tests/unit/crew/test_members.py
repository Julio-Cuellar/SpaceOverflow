"""Crew members: identity, validation and the roster file the seed reads."""

from __future__ import annotations

import pytest

from spaceapp.modules.crew.adapters.outbound.json_data import load_roster
from spaceapp.modules.crew.domain.members import CrewMember, crew_member_id
from spaceapp.platform.config import Settings
from spaceapp.platform.ids import habitat_id


def member(**changes: object) -> CrewMember:
    fields: dict[str, object] = {
        "habitat": "transit-ship",
        "code": "cdr",
        "name": "A. Garcia",
        "role": "Commander",
        "portrait": 1,
    }
    return CrewMember.create(**{**fields, **changes})  # type: ignore[arg-type]


def test_a_member_has_a_stable_identity_in_its_habitat() -> None:
    first, again = member(), member(name="A. Garcia Jr.")

    assert first.id == again.id == crew_member_id("transit-ship", "cdr")
    assert first.habitat_id == habitat_id("transit-ship")
    assert crew_member_id("transit-ship", "plt") != first.id


@pytest.mark.parametrize("portrait", [0, 5, -1])
def test_the_portrait_is_one_of_the_four_of_the_atlas(portrait: int) -> None:
    with pytest.raises(ValueError, match="portrait"):
        member(portrait=portrait)


@pytest.mark.parametrize("field", ["code", "name", "role"])
def test_text_fields_cannot_be_blank(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        member(**{field: "  "})


def test_the_roster_file_has_four_members_with_one_portrait_each() -> None:
    roster = load_roster(Settings().crew_roster_path)

    assert len(roster) == 4
    assert sorted(m.portrait for m in roster) == [1, 2, 3, 4]
    assert len({m.code for m in roster}) == 4
    assert {m.habitat_id for m in roster} == {habitat_id("transit-ship")}
