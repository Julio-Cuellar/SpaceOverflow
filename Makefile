UV ?= $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
COMPOSE = docker compose -f docker/compose.yaml

.PHONY: setup db-up db-down migrate lint types arch test cov check

setup:            ## install dependencies (Python 3.12 managed by uv)
	$(UV) sync

db-up:            ## PostgreSQL + pgvector in Docker
	$(COMPOSE) up -d --wait postgres

db-down:
	$(COMPOSE) down

migrate:          ## apply the platform migrations to the local database
	$(UV) run python -m spaceapp.platform.migrate platform

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

types:
	$(UV) run mypy

arch:             ## import-linter contracts between modules and layers
	$(UV) run lint-imports

test:
	$(UV) run pytest -q

cov:              ## tests with a minimum coverage of 80 %
	$(UV) run pytest -q --cov --cov-report=term-missing --cov-fail-under=80

check: lint types arch cov
