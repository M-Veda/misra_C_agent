.PHONY: dev test lint build migrate format up down logs health

COMPOSE := docker compose
COMPOSE_DEV := docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.prod.yml
COMPOSE_CI := docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.ci.yml

dev:
	$(COMPOSE_DEV) up --build

test:
	cd rule-engine && pip install -e . && pytest
	cd backend && pip install -e ../rule-engine && pip install -e ".[dev]" && pytest
	$(COMPOSE_CI) run --rm frontend npm run test
	cd clang-worker && cmake -B build -S . && cmake --build build && ctest --test-dir build --output-on-failure || true

lint:
	cd rule-engine && pip install -e . && ruff check src
	cd backend && pip install -e ../rule-engine && pip install -e ".[dev]" && ruff check src tests
	cd backend && mypy src
	cd frontend && npm run lint
	cd frontend && npm run typecheck

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) exec backend alembic upgrade head

format:
	cd backend && ruff format src tests
	cd backend && ruff check --fix src tests
	cd frontend && npm run format

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

health:
	curl -sf http://localhost:8000/api/v1/health
	curl -sf http://localhost:8000/api/v1/health/ready
	curl -sf http://localhost:8080/health
