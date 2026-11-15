"""Alembic environment for the `telemetry` schema (sensors, readings and scenarios)."""

from spaceapp.platform.migrations_env import run

run("telemetry")
