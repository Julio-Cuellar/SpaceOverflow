"""Exports the contracts consumed by Dev B's interface (task 5.4).

    uv run python -m spaceapp.interfaces.contracts_export           # writes contracts/
    uv run python -m spaceapp.interfaces.contracts_export --check   # fails if anything changed

`contracts/schema.graphql` is Dev B's draft and is left untouched: the full schema goes in
`schema.generated.graphql` and a test requires the draft to be a subset.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from spaceapp.interfaces.graphql.schema import schema
from spaceapp.modules.realtime.adapters.inbound.ws_schema import ws_messages_schema
from spaceapp.platform.config import ROOT, Settings
from spaceapp.platform.profiles import Profile


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _openapi() -> str:
    from spaceapp.main import create_app  # here, to avoid importing main when the module loads

    # With the development profile, so the operations routes (R8) also show up.
    return _json(create_app(Settings(profile=Profile.DEV1)).openapi())


CONTRACTS: dict[str, Callable[[], str]] = {
    "schema.generated.graphql": lambda: schema.as_str() + "\n",
    "openapi.json": _openapi,
    "ws-messages.schema.json": lambda: _json(ws_messages_schema()),
}


def render(name: str) -> str:
    return CONTRACTS[name]()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--out", type=Path, default=ROOT / "contracts")
    parser.add_argument(
        "--check", action="store_true", help="does not write; fails if there are changes"
    )
    args = parser.parse_args(argv)
    stale: list[str] = []
    for name in CONTRACTS:
        path: Path = args.out / name
        content = render(name)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"written {path}")
    if stale:
        print(f"stale: {', '.join(stale)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
