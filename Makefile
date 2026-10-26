.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check demo serve mcp graph docker \
	web-install web-dev web-check

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-12s %s\n", $$1, $$2}'

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

check: lint typecheck test ## Everything CI runs for the Python package

demo: ## Offline scripted tutoring session (no API key)
	uv run ai-tutor demo

serve: ## Run the API on http://127.0.0.1:8000
	uv run ai-tutor serve --reload

mcp: ## Run the MCP server over stdio
	uv run ai-tutor mcp

graph: ## Print the agent graph as Mermaid
	uv run ai-tutor graph

docker: ## Build and start the API and the web UI with Docker Compose
	docker compose up --build

web-install: ## Install the web UI's dependencies
	cd web && npm ci

web-dev: ## Run the web UI on http://localhost:3000 (start the API first)
	cd web && npm run dev

web-check: ## Everything CI runs for the web UI
	cd web && npm run lint && npm run typecheck && npm test && npm run build
