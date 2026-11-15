"""The contracts published for Dev B (task 5.4) are up to date with the code."""

from __future__ import annotations

from pathlib import Path

import pytest

from spaceapp.interfaces.contracts_export import CONTRACTS, main, render

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_the_published_file_matches_what_the_code_generates(name: str) -> None:
    published = (ROOT / "contracts" / name).read_text(encoding="utf-8")
    assert published == render(name), (
        f"contracts/{name} is stale: uv run python -m spaceapp.interfaces.contracts_export"
    )


def test_rendering_twice_gives_the_same_bytes() -> None:
    assert all(render(n) == render(n) for n in CONTRACTS)


def test_the_frontend_draft_is_not_overwritten() -> None:
    assert "schema.graphql" not in CONTRACTS, "contracts/schema.graphql is Dev B's draft"


def test_check_mode_fails_when_a_file_is_stale(tmp_path: Path) -> None:
    assert main(["--out", str(tmp_path)]) == 0
    assert main(["--out", str(tmp_path), "--check"]) == 0
    (tmp_path / "openapi.json").write_text("{}", encoding="utf-8")
    assert main(["--out", str(tmp_path), "--check"]) == 1
