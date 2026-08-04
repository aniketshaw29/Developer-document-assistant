# Developer Documentation Assistant — dev commands
# Backend runs from a venv at ./venv; frontend is a Vite app in ./frontend.

.PHONY: help setup venv install backend frontend dev test test-backend test-frontend lint build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: venv install ## One-time setup: create the venv and install dependencies

venv: ## Create the Python virtual environment
	python3.12 -m venv venv

install: ## Install backend + frontend dependencies
	venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

backend: ## Run the FastAPI backend on :8000
	venv/bin/uvicorn app.main:app --reload --port 8000 --app-dir backend

frontend: ## Run the Vite dev server on :5173
	cd frontend && npm run dev

dev: backend frontend ## Run backend and frontend together

test: test-backend test-frontend ## Run all tests

test-backend: ## Run the backend test suite
	cd backend && ../venv/bin/python -m pytest tests/ -q

test-frontend: ## Typecheck + lint the frontend
	cd frontend && npm run build && npm run lint

lint: ## Lint the frontend
	cd frontend && npm run lint

build: ## Build the frontend for production
	cd frontend && npm run build

clean: ## Remove generated data, caches and built assets
	rm -rf data/chroma backend/**/__pycache__ frontend/dist
