#!/usr/bin/env bash
# Full verification without depending on make: lint, types, architecture and tests with coverage.
set -euo pipefail
cd "$(dirname "$0")/.."
UV="${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}"
echo "== ruff";        "$UV" run ruff check . && "$UV" run ruff format --check .
echo "== mypy";        "$UV" run mypy
echo "== import-linter"; "$UV" run lint-imports
echo "== pytest + coverage"; "$UV" run pytest -q --cov --cov-report=term-missing --cov-fail-under=80
