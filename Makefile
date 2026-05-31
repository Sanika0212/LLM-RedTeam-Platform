.PHONY: help setup up down restart logs clean test migrate lint format install-backend install-frontend install-redteam

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup
	@echo "🔧 Setting up project..."
	cp .env.example .env
	@echo "✅ .env file created - please configure it with your API keys"
	@echo "Next steps:"
	@echo "  1. Edit .env file with your credentials"
	@echo "  2. Run 'make install-backend' to install Python dependencies"
	@echo "  3. Run 'make install-frontend' to install Node dependencies"
	@echo "  4. Run 'make up' to start services"

install-backend: ## Install backend dependencies
	@echo "📦 Installing backend dependencies..."
	cd backend && python -m venv venv && \
	. venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install

install-redteam: ## Install red-team engine dependencies
	@echo "📦 Installing red-team engine dependencies..."
	cd redteam-engine && python -m venv venv && \
	. venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

up: ## Start all services
	@echo "🚀 Starting services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "  - Backend: http://localhost:8000"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "🛑 Stopping services..."
	docker-compose down
	@echo "✅ Services stopped"

restart: down up ## Restart all services

logs: ## Show logs for all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-worker: ## Show worker logs
	docker-compose logs -f worker

clean: ## Clean up containers and cache
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

migrate: ## Run database migrations
	@echo "🗄️  Running database migrations..."
	docker-compose exec backend alembic upgrade head
	@echo "✅ Migrations complete"

test: ## Run all tests
	@echo "🧪 Running tests..."
	cd backend && pytest -v --cov=. --cov-report=html
	cd redteam-engine && pytest -v --cov=. --cov-report=html
	@echo "✅ Tests complete"

lint: ## Run linters
	@echo "🔍 Running linters..."
	cd backend && black --check . && isort --check .
	cd redteam-engine && black --check . && isort --check .

format: ## Format code
	@echo "✨ Formatting code..."
	cd backend && black . && isort .
	cd redteam-engine && black . && isort .

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d llm_redteam

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

dev-backend: ## Run backend locally
	cd backend && . venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend locally
	cd frontend && npm run dev

dev-worker: ## Run Celery worker locally
	cd backend && . venv/bin/activate && celery -A workers.eval_worker worker --loglevel=info

build: ## Build Docker images
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Build complete"

ps: ## Show running containers
	docker-compose ps

health: ## Check service health
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health || echo "Backend: DOWN"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: UP" || echo "Frontend: DOWN"
