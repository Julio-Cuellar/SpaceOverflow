import json
from pathlib import Path

from spaceapp.modules.telemetry.domain.layout import Layout
from spaceapp.modules.telemetry.domain.simulator import ZoneBaseline


def load_layout(path: Path | str) -> Layout:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    zones = tuple(
        ZoneBaseline(z["code"], z["temperature_c"], z["humidity_pct"], z["co2_mmhg"])
        for z in raw["zones"]
    )
    return Layout(habitat_code=raw["habitat_code"], zones=zones)
