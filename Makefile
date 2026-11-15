UV ?= $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
COMPOSE = docker compose -f docker/compose.yaml

.PHONY: setup db-up db-down migrate lint types arch test cov check

setup:            ## instala dependencias (Python 3.12 gestionado por uv)
	$(UV) sync

db-up:            ## PostgreSQL + pgvector en Docker
	$(COMPOSE) up -d --wait postgres

db-down:
	$(COMPOSE) down

migrate:          ## aplica las migraciones de la plataforma a la base local
	$(UV) run python -m spaceapp.platform.migrate platform

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

types:
	$(UV) run mypy

arch:             ## contratos de import-linter entre módulos y capas
	$(UV) run lint-imports

test:
	$(UV) run pytest -q

cov:              ## pruebas con cobertura mínima de 80 %
	$(UV) run pytest -q --cov --cov-report=term-missing --cov-fail-under=80

check: lint types arch cov
