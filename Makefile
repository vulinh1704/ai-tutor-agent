.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check demo serve graph docker

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install dependencies and git hooks
	uv sync --all-extras
	uv run pre-commit install

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-fix lint issues and format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Type-check the source
	uv run mypy

test: ## Run the test-suite with coverage
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test ## Everything CI runs

demo: ## Offline scripted tutoring session (no API key)
	uv run ai-tutor demo

serve: ## Run the API on http://127.0.0.1:8000
	uv run ai-tutor serve --reload

graph: ## Print the agent graph as Mermaid
	uv run ai-tutor graph

docker: ## Build and start the API with Docker Compose
	docker compose up --build
