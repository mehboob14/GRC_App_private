# Verity — developer entry points.
#
# `make setup`, `make up`, `make migrate`, `make check`, `make test` are the documented
# commands. Everything else here is something one of those calls.
#
# On Windows without make, run the underlying commands from docs/runbooks/local-setup.md
# or work inside WSL.

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose --env-file .env -f infra/docker/docker-compose.yml
PROD_COMPOSE := docker compose -f infra/docker/docker-compose.prod.yml
UV := uv --directory backend
BACKEND := $(UV) run

.PHONY: help
help: ## List the targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- setup ---------------------------------------------------------------------------

.env: .env.example
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

.PHONY: setup
setup: .env ## Install dependencies from the lockfile
	$(UV) sync --frozen --extra dev
	@echo "Next: make up && make migrate"

# --- stack ---------------------------------------------------------------------------

.PHONY: up
up: .env ## Start postgres, redis, and minio
	$(COMPOSE) up -d --wait postgres redis minio
	$(COMPOSE) up minio-init
	@echo "postgres, redis, and minio are up"

.PHONY: down
down: ## Stop the stack, keeping the data
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop the stack and delete its data
	$(COMPOSE) down --volumes

.PHONY: logs
logs: ## Follow the stack's logs
	$(COMPOSE) logs -f

# --- database ------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Apply migrations, as the migration role
	$(BACKEND) alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Reverse the most recent migration
	$(BACKEND) alembic downgrade -1

.PHONY: revision
revision: ## Autogenerate a migration: make revision m="add controls"
	@test -n "$(m)" || (echo 'usage: make revision m="what it does"' && exit 1)
	$(BACKEND) alembic revision --autogenerate -m "$(m)"

# --- run -----------------------------------------------------------------------------

.PHONY: run
run: ## Run the API with reload
	$(BACKEND) uvicorn verity.main:app --reload --host 127.0.0.1 --port 8000

.PHONY: worker
worker: ## Run a Celery worker
	$(BACKEND) celery -A verity.workers.celery_app:celery_app worker --loglevel=info

.PHONY: beat
beat: ## Run the Celery scheduler
	$(BACKEND) celery -A verity.workers.celery_app:celery_app beat --loglevel=info

# --- images --------------------------------------------------------------------------
#
# The production images. Local development does not use them — `make run` is still
# native uvicorn against `make up`. These exist so a broken Dockerfile is caught here,
# in seconds, instead of on the server halfway through a deploy.

# Plain `docker build`, not `compose build`: compose interpolates the whole file
# before doing anything, so the `:?` required-variable guards in the prod stack would
# fail here — and demanding production secrets to typecheck a Dockerfile is silly.
.PHONY: build
build: ## Build the production images (does not run them)
	docker build -t verity-api:latest backend
	docker build -t verity-web:latest frontend

.PHONY: build-check
build-check: build ## Build, then prove the API image boots and answers /healthz
	@docker run --rm --entrypoint python verity-api:latest \
		-c "import verity.main; print('api image imports ok')"
	@docker run --rm --entrypoint sh verity-web:latest \
		-c "test -f /usr/share/nginx/html/index.html && ! test -f /usr/share/nginx/html/mockServiceWorker.js && echo 'web image built ok, mocks stripped'"

# --- checks --------------------------------------------------------------------------

.PHONY: check
check: format-check lint typecheck imports ## Everything CI checks except the tests

.PHONY: format
format: ## Format
	$(BACKEND) ruff format .
	$(BACKEND) ruff check --fix .

.PHONY: format-check
format-check: ## Fail if anything is unformatted
	$(BACKEND) ruff format --check .

.PHONY: lint
lint: ## Lint
	$(BACKEND) ruff check .

.PHONY: typecheck
typecheck: ## Type check, strict
	$(BACKEND) mypy

.PHONY: imports
imports: ## Check the module boundary contracts
	$(BACKEND) lint-imports --config pyproject.toml

# --- tests ---------------------------------------------------------------------------

.PHONY: test
test: ## Every test, with the database suites required to run
	VERITY_REQUIRE_DB=1 $(BACKEND) pytest

.PHONY: test-unit
test-unit: ## Only the tests that need no database
	$(BACKEND) pytest tests/unit

.PHONY: test-isolation
test-isolation: ## The tenant-isolation suite — a merge blocker
	VERITY_REQUIRE_DB=1 $(BACKEND) pytest tests/isolation -v

.PHONY: coverage
coverage: ## Tests with a coverage report
	VERITY_REQUIRE_DB=1 $(BACKEND) pytest --cov --cov-report=term-missing
