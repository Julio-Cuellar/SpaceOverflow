"""The mission seed leaves the database with the story the console shows in its demo mode."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from spaceapp.devtools.seed_mission import SeedError, seed
from spaceapp.platform.config import Settings

pytestmark = pytest.mark.integration


async def test_the_seed_replays_a_mission_and_refuses_to_run_over_it(
    async_url: str, session_factory: Any
) -> None:
    settings = Settings(database_url=async_url)

    summary = await seed(settings, hours=2.5, clean=True, now=datetime.now(UTC))

    # The air history raised the CO₂ alert through the rules, not by hand.
    assert "env-co2-1h ALERT RAISED" in summary.alerts
    assert summary.readings > 10_000
    # The alert opened its incident; the second one was reported and acknowledged.
    assert any("High CO₂" in i and i.endswith("OPEN") for i in summary.incidents)
    assert any("ACKNOWLEDGED" in i for i in summary.incidents)
    # The day's tasks exist and Ground's plan went through the link and was confirmed.
    assert summary.tasks >= 7
    assert summary.plan == "v1 CONFIRMED"

    with pytest.raises(SeedError, match="--reset"):
        await seed(settings, hours=0.1, clean=False)
