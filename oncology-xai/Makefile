.PHONY: up down logs test lint fmt build clean install migrate

ENV_FILE ?= .env
DOCKER_COMPOSE = docker compose -f infra/docker-compose.yml --env-file $(ENV_FILE)

## Infrastructure

up: ## Start all services
	$(DOCKER_COMPOSE) up -d

down: ## Stop all services
	$(DOCKER_COMPOSE) down

logs: ## View logs
	$(DOCKER_COMPOSE) logs -f

ps: ## List running services
	$(DOCKER_COMPOSE) ps

build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

clean: ## Remove containers, volumes, images
	$(DOCKER_COMPOSE) down -v --rmi local

## Development

install: ## Install all Python packages (editable)
	pip install -e packages/common
	pip install -e packages/event-contracts
	pip install -e packages/langgraph-workflows
	pip install -e apps/api-gateway
	pip install -e apps/case-service
	pip install -e apps/image-service
	pip install -e apps/inference-service
	pip install -e apps/ehr-service
	pip install -e apps/graph-service
	pip install -e apps/ontology-admin-service
	pip install -e apps/audit-service

install-webapp: ## Install webapp deps
	cd apps/webapp && npm install

## Database

migrate: ## Run Alembic migrations
	cd apps/case-service && alembic upgrade head
	cd apps/image-service && alembic upgrade head
	cd apps/inference-service && alembic upgrade head
	cd apps/ehr-service && alembic upgrade head
	cd apps/graph-service && alembic upgrade head
	cd apps/ontology-admin-service && alembic upgrade head
	cd apps/audit-service && alembic upgrade head

## Testing

test: ## Run all tests
	pytest packages/common/tests/ -v
	pytest packages/event-contracts/tests/ -v
	pytest apps/case-service/tests/ -v
	pytest apps/image-service/tests/ -v
	pytest apps/inference-service/tests/ -v
	pytest apps/ehr-service/tests/ -v
	pytest apps/graph-service/tests/ -v
	pytest apps/audit-service/tests/ -v

test-service: ## Run tests for SERVICE=<name>
	cd apps/$(SERVICE) && pytest tests/ -v

## Code Quality

lint: ## Run linters
	ruff check packages/ apps/ --exclude=apps/webapp
	mypy packages/ apps/ --ignore-missing-imports --exclude=apps/webapp

fmt: ## Format code
	ruff check --fix packages/ apps/ --exclude=apps/webapp
	black packages/ apps/ --exclude=apps/webapp

## OpenAPI

openapi-export: ## Export OpenAPI specs
	@mkdir -p docs/openapi
	curl -s http://localhost:8000/openapi.json > docs/openapi/api-gateway.json || true
	curl -s http://localhost:8001/openapi.json > docs/openapi/case-service.json || true
	curl -s http://localhost:8002/openapi.json > docs/openapi/image-service.json || true
	curl -s http://localhost:8003/openapi.json > docs/openapi/inference-service.json || true
	curl -s http://localhost:8004/openapi.json > docs/openapi/ehr-service.json || true
	curl -s http://localhost:8005/openapi.json > docs/openapi/graph-service.json || true
	curl -s http://localhost:8006/openapi.json > docs/openapi/ontology-admin-service.json || true
	curl -s http://localhost:8007/openapi.json > docs/openapi/audit-service.json || true

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
